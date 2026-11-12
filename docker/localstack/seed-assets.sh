#!/bin/sh
set -eu

bucket="ragtaurant-assets"
assets="/opt/ragtaurant-assets"

if ! awslocal s3api head-bucket --bucket "$bucket" >/dev/null 2>&1; then
  awslocal s3api create-bucket --bucket "$bucket"
fi

# The bucket stays private: only the backend reads it, using its own credentials.
awslocal s3 sync "$assets" "s3://$bucket/menu" \
  --cache-control "public, max-age=86400" \
  --only-show-errors
