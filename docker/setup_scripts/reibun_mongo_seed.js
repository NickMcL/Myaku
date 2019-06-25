db = db.getSiblingDB('admin')

db.createUser(
    {
        user: backup_db_username,
        pwd: backup_db_password,
        roles: [ { role: "backup", db: "admin" } ]
    }
)

db = db.getSiblingDB(reibun_db_name)

db.createUser(
    {
        user: crawler_db_username,
        pwd: crawler_db_password,
        roles: [ { role: "readWrite", db: "reibun" } ]
    }
)