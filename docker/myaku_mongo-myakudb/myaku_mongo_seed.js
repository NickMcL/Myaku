db = db.getSiblingDB('admin')

db.createUser(
    {
        user: backup_db_username,
        pwd: backup_db_password,
        roles: [ { role: "backup", db: "admin" } ]
    }
)

db = db.getSiblingDB(myaku_db_name)

db.createUser(
    {
        user: crawler_db_username,
        pwd: crawler_db_password,
        roles: [ { role: "readWrite", db: "myaku" } ]
    }
)

db.createUser(
    {
        user: web_db_username,
        pwd: web_db_password,
        roles: [ { role: "read", db: "myaku" } ]
    }
)
