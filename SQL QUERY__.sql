USE plant;

#SHOW GLOBAL VARIABLES LIKE 'local_infile';

#SHOW TABLES LIKE 'production';


CREATE TABLE utcl_data (
    TRIP_ID VARCHAR(50),
    SEQ_LOADER INT,
    SEQ_PACKER INT,
    PLANT_CODE VARCHAR(10),
    MATERIAL_CODE VARCHAR(120),
    TOTAL_QTY INT,
    PACK_TYPE VARCHAR(20),
    GRDAE VARCHAR(20), 
    BRAND VARCHAR(20),
    GateIn DATETIME,
    GateOut DATETIME
    );

drop table utcl_Data
DESCRIBE production;
-- or
SHOW COLUMNS FROM production;

-- Turn it on now
SET GLOBAL local_infile = 1;

-- Verify
SHOW VARIABLES LIKE 'secure_file_priv';

SHOW GLOBAL VARIABLES LIKE 'local_infile';

use plant;
LOAD DATA LOCAL INFILE "C:/Users/User/Downloads/5yrs_PMR_DATA_/ALL CSV/UTCL_1-4-2024_TO_31-3-2025____.csv"
INTO TABLE utcl_data
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(TRIP_ID,SEQ_LOADER, SEQ_PACKER, PLANT_CODE, MATERIAL_CODE, TOTAL_QTY, PACK_TYPE, GRDAE, BRAND, @GateIn, @GateOut)
SET GateIn  = STR_TO_DATE(@GateIn,  '%Y-%m-%d %H:%i:%s'),
    GateOut = STR_TO_DATE(@GateOut, '%Y-%m-%d %H:%i:%s');

select COUNT(*) from UTCL_DATA where trip_id = '5000171671'
    
    Error Code: 2068. LOAD DATA LOCAL INFILE file request rejected due to restrictions on access.




  drop table utcl_data
use plant;

SHOW TABLES;
DESCRIBE Utcl_Data;

SELECT COUNT(*) AS total_rows 
FROM utcl_data;
use plant;
use plant;
select * from utcL_data where trip_id ="1001775213"

USE plant;
SELECT
    TRIP_ID,
    COUNT(*) AS row_count
FROM
    utcl_data
GROUP BY
    -- List all column names here
    trip_id
HAVING
    COUNT(*) > 1;
    
    use plant;
    SELECT
    COUNT(*) AS unique_combinations_count
FROM
    (
        SELECT DISTINCT
            material_code,
            pack
        FROM
            utcl_data
    ) AS unique_data;
    
    select material_code from utcl_Data where pack_type  ='null'
SELECT DISTINCT
    material_code, pack_type
    
FROM
    utcl_data;
