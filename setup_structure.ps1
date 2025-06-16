# Tạo hàm hỗ trợ tạo file nếu chưa tồn tại
function New-EmptyFile {
    param (
        [string]$Path
    )
    if (-not (Test-Path $Path)) {
        New-Item -ItemType File -Path $Path | Out-Null
    }
}

# Thư mục gốc
$root = "ChatApp"

# Tạo thư mục
$dirs = @(
    "$root/client/gui/assets/icons",
    "$root/client/gui/assets/images",
    "$root/client/network",
    "$root/client/models",
    "$root/client/utils",
    "$root/server/database",
    "$root/server/models",
    "$root/server/network"
)

foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}

# Danh sách file cần tạo
$files = @(
    "$root/client/gui/__init__.py",
    "$root/client/gui/login.py",
    "$root/client/gui/main_window.py",
    "$root/client/gui/chat_window.py",
    "$root/client/gui/nearby_users.py",
    "$root/client/network/__init__.py",
    "$root/client/network/client_socket.py",
    "$root/client/network/protocol.py",
    "$root/client/models/__init__.py",
    "$root/client/models/user.py",
    "$root/client/models/message.py",
    "$root/client/models/group.py",
    "$root/client/utils/__init__.py",
    "$root/client/utils/config.py",
    "$root/client/utils/helpers.py",
    "$root/client/main.py",
    "$root/server/__init__.py",
    "$root/server/server.py",
    "$root/server/config.py",
    "$root/server/database/__init__.py",
    "$root/server/database/db_connection.py",
    "$root/server/database/queries.py",
    "$root/server/models/__init__.py",
    "$root/server/models/user.py",
    "$root/server/models/message.py",
    "$root/server/models/group.py",
    "$root/server/network/__init__.py",
    "$root/server/network/server_socket.py",
    "$root/server/network/protocol.py",
    "$root/requirements.txt",
    "$root/README.md",
    "$root/run.sh"
)

foreach ($file in $files) {
    New-EmptyFile -Path $file
}

Write-Host "✅ Cấu trúc thư mục ChatApp đã được tạo thành công."
