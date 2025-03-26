-- 創建資料表 `device`
CREATE TABLE device (
    device_id TEXT NOT NULL,
    device_name TEXT NOT NULL,
    device_network TEXT,
    device_address TEXT,
    device_temperature REAL,
    device_humidity REAL,
    take_time INTEGER NOT NULL,
    temp INTEGER NOT NULL,
    take_photo INTEGER NOT NULL,
    photo_take INTEGER NOT NULL,
    PRIMARY KEY (device_id)
);

-- 插入資料到 `device`（從 A1 到 A5）
INSERT INTO device (device_id, device_name, device_network, device_address, device_temperature, device_humidity, take_time, temp, take_photo, photo_take) VALUES
('A1', 'Device1', NULL, '25.034392633619827,121.3919934576628', NULL, NULL, 2000, 5, 1, 0),
('A2', 'Device2', NULL, '25.034392633619827,121.3919934576628', NULL, NULL, 2000, 5, 1, 0),
('A3', 'Device3', NULL, '25.034392633619827,121.3919934576628', NULL, NULL, 2000, 5, 1, 0),
('A4', 'Device4', NULL, '25.034392633619827,121.3919934576628', NULL, NULL, 2000, 5, 1, 0),
('A5', 'Device5', NULL, '25.034392633619827,121.3919934576628', NULL, NULL, 2000, 5, 1, 0);

-- 創建資料表 `mosquito`
CREATE TABLE mosquito (
    mosquito_id TEXT NOT NULL,
    mosquito_name TEXT NOT NULL,
    PRIMARY KEY (mosquito_id)
);

-- 插入資料到 `mosquito`
INSERT INTO mosquito (mosquito_id, mosquito_name) VALUES
('0', 'H'),
('1', 'IG'),
('2', 'W'),
('3', 'WH'),
('4', 'GR');

-- 創建資料表 `photo`（添加 processed 欄位）
CREATE TABLE photo (
    photo_id TEXT NOT NULL,
    photo_address TEXT,
    photo_location TEXT,
    photo_time TEXT,
    photo_storage TEXT,
    device_id TEXT,
    msg TEXT NOT NULL,
    count INTEGER NOT NULL,
    processed INTEGER DEFAULT 0,  -- 新增欄位
    PRIMARY KEY (photo_id),
    FOREIGN KEY (device_id) REFERENCES device(device_id)
);

-- 創建資料表 `seg_photo`
CREATE TABLE seg_photo (
    SP_id INTEGER PRIMARY KEY AUTOINCREMENT,
    photo_id TEXT,
    mosquito_id TEXT,
    SP_storage TEXT,
    x1 REAL,
    y1 REAL,
    x2 REAL,
    y2 REAL,
    new INTEGER,
    FOREIGN KEY (photo_id) REFERENCES photo(photo_id),
    FOREIGN KEY (mosquito_id) REFERENCES mosquito(mosquito_id)
);

-- 創建資料表 `user`
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_line TEXT NOT NULL,
    device_id TEXT,
    FOREIGN KEY (device_id) REFERENCES device(device_id)
);

-- 創建索引
CREATE INDEX idx_photo_device_id ON photo(device_id);
CREATE INDEX idx_seg_photo_photo_id ON seg_photo(photo_id);
CREATE INDEX idx_seg_photo_mosquito_id ON seg_photo(mosquito_id);
CREATE INDEX idx_user_device_id ON user(device_id);