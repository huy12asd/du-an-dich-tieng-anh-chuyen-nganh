#!/usr/bin/env bash
# exit on error
set -o errexit

# Cài đặt các gói cần thiết của hệ thống
apt-get update
apt-get install -y curl gnupg

# Thêm khoá Microsoft GPG
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -

# Thêm repository của Microsoft
curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list

# Cập nhật lại danh sách gói và cài đặt driver
apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql17 unixodbc-dev

# Cài đặt các thư viện Python
pip install -r requirements.txt