export DATABASE_NAME=bb_master
export DATABASE_PASSWORD=bb_master
export DATABASE_USER=bb_master
export SUPERUSER=foo@example.com
export SUPERUSER_PASSWORD=foo
export BUCKET_NAME=bigbot-staging
export PORT=8000
export APP_PROJECT=project
export APPNAME=bigbot-main


export CUSTOMER_ID=bigbot-main
export CUSTOMER_DB_STAGING=${CUSTOMER_ID}-staging
export CUSTOMER_DB_USER_STAGING=${CUSTOMER_ID}-staging
export CUSTOMER_DB_PASSWORD_STAGING=`date +%s | sha256sum | base64 | head -c 32 ; echo`
export CUSTOMER_DB_PRODUCTION=${CUSTOMER_ID}-production
export CUSTOMER_DB_USER_PRODUCTION=${CUSTOMER_ID}-production
export CUSTOMER_DB_PASSWORD_PRODUCTION=`date +%s | sha256sum | base64 | head -c 32 ; echo`
