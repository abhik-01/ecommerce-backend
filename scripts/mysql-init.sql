CREATE DATABASE IF NOT EXISTS userservice CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS productservice CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS orderservice CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS paymentservice CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS notificationservice CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON userservice.* TO 'root'@'%';
GRANT ALL PRIVILEGES ON productservice.* TO 'root'@'%';
GRANT ALL PRIVILEGES ON orderservice.* TO 'root'@'%';
GRANT ALL PRIVILEGES ON paymentservice.* TO 'root'@'%';
GRANT ALL PRIVILEGES ON notificationservice.* TO 'root'@'%';
FLUSH PRIVILEGES;
