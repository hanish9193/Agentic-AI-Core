import sys
import os
sys.path.append(os.getcwd())

from backend.utils.crypto import decrypt_value

enc_user = "gAAAAABqWvrVQZjnKK_sk6BozMj811yiSEy-3EXzZ_0i9HK5iRB9DYxJ9qD-POIXkhoyWt1RLVq8cFNRFAiZfBb4t_Va1F_N5Q=="
enc_pass = "gAAAAABqWvrVqRA42_x6BKOIJAB5wt9sw7KG_O_i6ymTxK71BYABdb5pW_iOB2UToFm_AILzRb5frzCd6yPOW0lO7eqB9IbBqg=="

print("Decrypted User:", decrypt_value(enc_user))
print("Decrypted Pass:", decrypt_value(enc_pass))
