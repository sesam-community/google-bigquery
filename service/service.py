import pprint
import sys
import json
from flask import Flask, request, Response, abort
from google.cloud import bigquery
from sesamutils import VariablesConfig, sesam_logger
from sesamutils.flask import serve

app = Flask(__name__)

required_env_vars = ["GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_APPLICATION_CREDENTIALS_CONTENT", "QUERY_CONFIGS"]
optional_env_vars = [("DEFAULT_PAGE_SIZE", 100)]

env_config = VariablesConfig(required_env_vars, optional_env_vars)
if not env_config.validate():
    sys.exit(1)

logger = sesam_logger('google-bigquery', app=app)

env_config.QUERY_CONFIGS = json.loads(env_config.QUERY_CONFIGS)
env_config.DEFAULT_PAGE_SIZE = int(env_config.DEFAULT_PAGE_SIZE)


logger.info('started up with\n\tGOOGLE_APPLICATION_CREDENTIALS:{}\n\tQUERY_CONFIGS:{}'.format(env_config.GOOGLE_APPLICATION_CREDENTIALS, env_config.QUERY_CONFIGS))

# write out service config from env var to known file
if env_config.GOOGLE_APPLICATION_CREDENTIALS:
    with open(env_config.GOOGLE_APPLICATION_CREDENTIALS, "wb") as out_file:
        out_file.write(env_config.GOOGLE_APPLICATION_CREDENTIALS_CONTENT.encode())



def stream_rows(query_key, since, limit, page_size):
    is_first_yield = True
    query_config = env_config.QUERY_CONFIGS.get(query_key)
    if since:
        query = query_config.get('updated_query')
        query_params = [
            bigquery.ScalarQueryParameter("since", query_config.get('updated_column').get('data_type'), since)
        ]
    else:
        query = query_config.get('query')
        query_params = []

    job_config = bigquery.QueryJobConfig()
    job_config.query_parameters = query_params

    # Explicitly use service account credentials by specifying the private key file
    client = bigquery.Client().from_service_account_json(env_config.GOOGLE_APPLICATION_CREDENTIALS)
    query_job = client.query(query, job_config=job_config)  # API request
    rows = query_job.result(page_size=page_size, max_results=limit)  # Waits for query to finish

    field_names = [r.name for r in rows.schema]

    updated_column_name = query_config.get('updated_column',{}).get('name')
    pk_columns = query_config.get('primary_key',[])
    logger.debug(f'fetching {rows.total_rows} rows')
    yield '['
    for row in rows:
        try:
            entity = {x: str(row.get(x)) for x in field_names}
            if updated_column_name:
                entity["_updated"] = str(row.get(updated_column_name))
            if pk_columns:
                _id_parts = [str(entity.get(pk_column,"")) for pk_column in pk_columns]
                entity["_id"] = "_".join(_id_parts)

            if is_first_yield:
                is_first_yield = False
            else:
                yield ','
            yield json.dumps(entity)
        except IndexError:
            results = None
    yield ']'

@app.route("/query", methods=["GET"])
def get_data():
    query_key = request.args.get("ms_query_key")
    since = request.args.get("since")
    limit = int(request.args.get("limit")) if request.args.get("limit") else None
    page_size = int(request.args.get("ms_page_size", env_config.DEFAULT_PAGE_SIZE))

    if not query_key:
        abort(400, "ms_query_key query parameter is mandatory")
    try:
        return Response(response=stream_rows(query_key, since, limit, page_size))
    except Exception as err:
        logger.exception(err)
        abort(500, str(err))

if __name__ == "__main__":
    serve(app)
