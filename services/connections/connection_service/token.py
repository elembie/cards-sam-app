import json
import time
import logging
import urllib.request
from jose import jwk, jwt
from jose.utils import base64url_decode

log = logging.getLogger()
log.setLevel(logging.INFO)

region = 'ap-southeast-2'
userpool_id = 'ap-southeast-2_H9SN2bqby'
app_client_id = '7s15kdmtc3rp33tct70en9u7d0'
keys_url = f'https://cognito-idp.{region}.amazonaws.com/{userpool_id}/.well-known/jwks.json'

with urllib.request.urlopen(keys_url) as f:
  response = f.read()
keys = json.loads(response.decode('utf-8'))['keys']

# https://github.com/awslabs/aws-support-tools/blob/master/Cognito/decode-verify-jwt/decode-verify-jwt.py

def validate_and_decode(token):

    # get the kid from the headers prior to verification
    headers = jwt.get_unverified_headers(token)
    kid = headers['kid']

    # search for the kid in the downloaded public keys
    key_index = -1
    for i in range(len(keys)):
        if kid == keys[i]['kid']:
            key_index = i
            break

    if key_index == -1:
        log.error('Public key not found in jwks.json')
        return None

    # construct the public key
    public_key = jwk.construct(keys[key_index])

    # get the last two sections of the token,
    # message and signature (encoded in base64)
    message, encoded_signature = str(token).rsplit('.', 1)

    # decode the signature
    decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))

    # verify the signature
    if not public_key.verify(message.encode("utf8"), decoded_signature):
        log.warn('Signature verification failed')
        return None

    log.info('Signature successfully verified')

    # since we passed the verification, we can now safely
    # use the unverified claims
    claims = jwt.get_unverified_claims(token)

    # additionally we can verify the token expiration
    if time.time() > claims['exp']:
        log.warn('Token is expired')
        return None

    # and the Audience  (use claims['client_id'] if verifying an access token)
    if claims['aud'] != app_client_id:
        log.warn('Token was not issued for this audience')
        return None

    # now we can use the claims
    log.info(f'JWT claims: {claims}')
    return claims
