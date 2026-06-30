import bcrypt
hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt())
print(hash.decode())
