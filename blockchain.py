from web3 import Web3
from eth_account import Account
import json
import ipfshttpclient
import os
from datetime import datetime

class BlockchainManager:
    def __init__(self):
        self.blockchain_enabled = False
        self.ipfs_enabled = False
        
        try:
            # Try to connect to Ethereum node
            self.w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
            if self.w3.is_connected():
                self.blockchain_enabled = True
                # Load the smart contract ABI and address
                with open('contracts/ExpenseTracker.json', 'r') as f:
                    contract_data = json.load(f)
                    self.contract_abi = contract_data['abi']
                    self.contract_address = contract_data['address']
                    
                self.contract = self.w3.eth.contract(
                    address=self.contract_address,
                    abi=self.contract_abi
                )
        except Exception as e:
            print(f"Ethereum connection failed: {str(e)}")
            self.blockchain_enabled = False
            
        try:
            # Try to connect to IPFS
            self.ipfs_client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
            self.ipfs_enabled = True
        except Exception as e:
            # Suppress IPFS connection error
            self.ipfs_enabled = False
        
    def store_expense(self, user_address, expense_data):
        """
        Store expense data on the blockchain if enabled
        """
        if not self.blockchain_enabled:
            return {'status': 'blockchain_disabled'}
            
        try:
            # Store receipt image in IPFS if enabled
            receipt_hash = None
            if self.ipfs_enabled:
                receipt_hash = self._store_in_ipfs(expense_data['receipt_path'])
            else:
                receipt_hash = "local_storage"
            
            # Prepare transaction
            transaction = self.contract.functions.addExpense(
                user_address,
                int(expense_data['amount'] * 100),  # Convert to cents
                expense_data['category'],
                receipt_hash,
                int(datetime.now().timestamp())
            ).build_transaction({
                'from': user_address,
                'nonce': self.w3.eth.get_transaction_count(user_address),
                'gas': 2000000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(
                transaction,
                private_key=os.getenv('PRIVATE_KEY')  # Store this securely
            )
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            return self.w3.eth.wait_for_transaction_receipt(tx_hash)
        except Exception as e:
            return {'error': str(e)}
    
    def _store_in_ipfs(self, file_path):
        """
        Store file in IPFS and return the hash
        """
        if not self.ipfs_enabled:
            return "local_storage"
            
        try:
            result = self.ipfs_client.add(file_path)
            return result['Hash']
        except Exception as e:
            print(f"IPFS storage failed: {str(e)}")
            return "local_storage"
    
    def get_expense_history(self, user_address):
        """
        Retrieve expense history for a user
        """
        if not self.blockchain_enabled:
            return []
            
        try:
            return self.contract.functions.getUserExpenses(user_address).call()
        except Exception as e:
            print(f"Failed to get expense history: {str(e)}")
            return []
    
    def verify_expense(self, expense_id):
        """
        Verify if an expense exists on the blockchain
        """
        if not self.blockchain_enabled:
            return False
            
        try:
            return self.contract.functions.verifyExpense(expense_id).call()
        except Exception as e:
            print(f"Failed to verify expense: {str(e)}")
            return False 