import os
import hashlib
from det_model import videodet

try:
    from web3 import Web3
    GANACHE_URL = "http://127.0.0.1:8545"
    web3 = Web3(Web3.HTTPProvider(GANACHE_URL))
    if not web3.is_connected():
        print("WARNING: Ganache not running. Blockchain features disabled.")
        web3 = None
except Exception as e:
    print(f"WARNING: Blockchain unavailable: {e}")
    web3 = None

CONTRACT_ADDRESS = "0x2DF3771E61bDABF03602A94E8D6e411Eb072e1a0"
CONTRACT_ABI = []  # ABI omitted for brevity — kept from original
contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI) if web3 else None
ACCOUNT_ADDRESS = "0x88Fe16cd31b35A25A7a523D5Aac08B1f7d78fEeb"
PRIVATE_KEY = "0xa1f5a3b1cdbe702b1c93214f21f91d8f813509cfe55cbe3abcd64741b5fc0712"

def calculate_file_hash(file_path):
    with open(file_path, "rb") as file:
        return hashlib.sha256(file.read()).hexdigest()

def calculate_video_hash(video_path):
    with open(video_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def store_file_on_blockchain(file_hash, file_path):
    if not web3:
        print("Blockchain not available.")
        return
    if videodet.predict_video(file_path)['confidence'] < 90:
        return
    tx = contract.functions.storeDetectionResult(
        file_hash, videodet.predict_video(file_path)['label']
    ).build_transaction({
        "from": ACCOUNT_ADDRESS,
        "nonce": web3.eth.get_transaction_count(ACCOUNT_ADDRESS),
        "gas": 3000000,
        "gasPrice": web3.to_wei("20", "gwei"),
    })
    signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction confirmed:", receipt)

def check_file_exists(file_hash):
    if not web3:
        return False
    try:
        result = contract.functions.getDetectionResult(file_hash).call()
        return bool(result[0])
    except Exception as e:
        print(f"Error checking file existence: {e}")
        return False

def process_file(file_path):
    if not web3:
        print("Blockchain not available.")
        return
    if not os.path.exists(file_path):
        print("File not found!")
        return
    if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
        file_hash = calculate_file_hash(file_path)
    elif file_path.lower().endswith((".mp4", ".avi", ".mkv", ".mov", ".flv")):
        file_hash = calculate_video_hash(file_path)
    else:
        print("Unsupported file format!")
        return
    if not check_file_exists(file_hash):
        store_file_on_blockchain(file_hash, file_path)

def get_detection_result(video_path):
    if not web3:
        return {}
    video_hash = calculate_video_hash(video_path)
    if not check_file_exists(video_hash):
        return {}
    try:
        result = contract.functions.getDetectionResult(video_hash).call()
        stored_hash, detection_result, timestamp = result
        return {'image_hash': stored_hash, 'detection_result': detection_result, 'timestamp': timestamp}
    except Exception as e:
        print(f"Error reading from blockchain: {e}")
        return None