#!/bin/sh
set -eu

bucket="ragtaurant-assets"
assets="/opt/ragtaurant-assets"

if ! awslocal s3api head-bucket --bucket "$bucket" >/dev/null 2>&1; then
  awslocal s3api create-bucket --bucket "$bucket"
fi

awslocal s3api put-bucket-policy \
  --bucket "$bucket" \
  --policy "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"PublicReadForLocalDemo\",\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":\"s3:GetObject\",\"Resource\":\"arn:aws:s3:::$bucket/*\"}]}"

awslocal s3 sync "$assets" "s3://$bucket/menu" \
  --cache-control "public, max-age=86400" \
  --only-show-errors
