import nacl.signing
import base64

key_pair = nacl.signing.SigningKey.generate()
public_key = key_pair.verify_key

private_key_base64 = base64.b64encode(key_pair.encode()).decode()
public_key_base64 = base64.b64encode(public_key.encode()).decode()

print(private_key_base64)
print(public_key_base64)