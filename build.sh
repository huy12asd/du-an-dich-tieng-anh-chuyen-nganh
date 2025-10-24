#!/usr/bin/env bash
# exit on error
set -o errexit

# Thêm "sudo" vào trước các lệnh hệ thống
sudo apt-get update
sudo apt-get install -y curl gnupg

# Thêm khoá Microsoft GPG với quyền sudo
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -

# Thêm repository của Microsoft (dùng tee để ghi file với quyền sudo)
curl https://packages.microsoft.com/config/debian/11/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list

# Cập nhật và cài đặt driver với sudo
sudo apt-get update
ACCEPT_EULA=Y sudo apt-get install -y msodbcsql17 unixodbc-dev

# Cài đặt các thư viện Python KHÔNG cần sudo
pip install -r requirements.txt