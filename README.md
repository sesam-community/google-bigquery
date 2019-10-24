# google-bigquery

[![Build Status](https://travis-ci.org/sesam-community/google-bigquery.svg?branch=master)](https://travis-ci.org/sesam-community/google-bigquery)

# azure-storage
Can be used to
 * execute a query and read the resultset into sesam

#### Features
 * supports continuity queries
 * supports sesam pull protocol

 ### Environment Parameters

 | CONFIG_NAME        | DESCRIPTION           | IS_REQUIRED  |DEFAULT_VALUE|
 | -------------------|---------------------|:------------:|:-----------:|
 | GOOGLE_APPLICATION_CREDENTIALS | file with optional path to save the service account key file content to | yes | n/a |
 | GOOGLE_APPLICATION_CREDENTIALS_CONTENT | service account key file content | yes | n/a |
 | QUERY_CONFIGS | dict where keys are query-keys and values are configuration per query. See details below  | yes | check the code |
 | LOG_LEVEL | log level. either of  | no | INFO |


 ##### QUERY_CONFIGS schema:
    QUERY_CONFIGS is dict with keys as query-config-key and values as config content.
    Config content is a dict with following fields along with their explanations:
      "primary_key": "list of columns to to compose the entity id with"
      "query" : "full scan query"
      "updated_column": {
        "name" : name of the updated_column,
        "data_type": dataype of the updated_column in the query. must be one of google-big-query StandardSqlDataTypes¹
      },
      "updated_query": updated_query where since parameter is written as "@since" instead of ":since"

¹ [google-big-query StandardSqlDataType](https://googleapis.dev/python/bigquery/latest/gapic/v2/enums.html#google.cloud.bigquery_v2.gapic.enums.StandardSqlDataType)

 ### Query Parameters

 | CONFIG_NAME        | DESCRIPTION           | IS_REQUIRED  |DEFAULT_VALUE|
 | -------------------|---------------------|:------------:|:-----------:|
 | ms_query_key | key to the query config that is to be loaded | yes | n/a |
 | ms_page_size² | number of rows to fetch and stream per page | no | 100 |
 | limit² | sesam pull protocol's "limit" parameter number of entities to be returned. Bound to the limit phrase in the query and page size in the config | no | <no limit> |
 | since | sesam pull protocol's "since" parameter  | no | 12H |

 ² <span style="font-family:Papyrus; font-size:0.5em;">effective value depends on the (A)limit clause in the query, (B)limit query_parameter and (C) ms_page_size parameter. First (A) is applied. Thereafter the lowest multiple of (C) following (B) is picked.</span>


 ### An example of system config:

 ```json
 {
   "_id": "my-google-bq-system",
   "type": "system:microservice",
   "connect_timeout": 60,
   "docker": {
     "environment": {
       "GOOGLE_APPLICATION_CREDENTIALS": "service-account-key.json",
       "GOOGLE_APPLICATION_CREDENTIALS_CONTENT": "$SECRET(service-account-key-content)",
       "QUERY_CONFIGS": {
         "my_query": {
           "primary_key": ["col1"],
           "query": "SELECT col1, col2 from mytable",
           "updated_column": {
             "name": "col2",
             "data_type": "TIMESTAMP"
           },
           "updated_query": "SELECT col1, col2 from mytable where col2 > @since"
         }
       }
     },
     "image": "sesamcommunity/google-bigquery:v0.1",
     "port": 5000
   },
   "read_timeout": 7200
 }

 ```

### An example of input-pipe config:
```json
{
  "_id": "gbq-hafslund-mdm-meterpoint-maxeffect",
  "type": "pipe",
  "source": {
    "type": "json",
    "system": "my-google-bq-system",
    "is_chronological": false,
    "is_since_comparable": true,
    "supports_since": true,
    "url": "query?ms_query_key=my_query"
  },
  "transform": {
    "type": "dtl",
    "rules": {
      "default": [
        ["copy", "*"]
      ]
    }
  }
}


  ```
