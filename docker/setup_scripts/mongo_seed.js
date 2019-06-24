db = db.getSiblingDB(reibun_db_name)

db.createUser(
    {
        user: crawler_db_username,
        pwd: crawler_db_password,
        roles: [ { role: "readWrite", db: "reibun" } ]
    }
)
