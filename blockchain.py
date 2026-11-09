import hashlib
import json
import time
import threading
from datetime import datetime
from typing import List, Dict, Optional
import uuid


class Block:
    def __init__(self, index: int, timestamp: str, data: dict, previous_hash: str):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty: int = 2):
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()


class Blockchain:
    def __init__(self):
        self.chain: List[Block] = []
        self.pending_transactions: List[dict] = []
        self.difficulty = 2
        self.mining_reward = 1
        self.create_genesis_block()
        self._lock = threading.Lock()

    def create_genesis_block(self):
        genesis_block = Block(0, datetime.now().isoformat(), {
            "type": "genesis",
            "message": "政务审批区块链系统创世区块"
        }, "0")
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)

    def get_latest_block(self) -> Block:
        return self.chain[-1]

    def add_block(self, data: dict) -> Block:
        with self._lock:
            previous_block = self.get_latest_block()
            new_block = Block(
                len(self.chain),
                datetime.now().isoformat(),
                data,
                previous_block.hash
            )
            new_block.mine_block(self.difficulty)
            self.chain.append(new_block)
            return new_block

    def is_chain_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            if current_block.hash != current_block.calculate_hash():
                return False

            if current_block.previous_hash != previous_block.hash:
                return False

        return True

    def get_all_transactions(self) -> List[dict]:
        transactions = []
        for block in self.chain:
            if block.data.get("type") != "genesis":
                transactions.append({
                    "block_index": block.index,
                    "timestamp": block.timestamp,
                    "hash": block.hash,
                    **block.data
                })
        return transactions

    def search_transactions(self, start_time: str = None, end_time: str = None, 
                           operator: str = None, stage: str = None) -> List[dict]:
        transactions = []
        for block in self.chain:
            if block.data.get("type") == "genesis":
                continue

            tx = {
                "block_index": block.index,
                "timestamp": block.timestamp,
                "hash": block.hash,
                **block.data
            }

            if start_time:
                try:
                    if block.timestamp < start_time:
                        continue
                except:
                    pass

            if end_time:
                try:
                    if block.timestamp > end_time:
                        continue
                except:
                    pass

            if operator:
                tx_operator = block.data.get("operator", "")
                if operator.lower() not in tx_operator.lower():
                    continue

            if stage:
                tx_stage = block.data.get("stage") or block.data.get("from_stage") or block.data.get("to_stage")
                if tx_stage and stage.lower() not in tx_stage.lower():
                    continue

            transactions.append(tx)

        return transactions


class GovernmentApprovalSystem:
    # 流程阶段
    STAGES = {
        "apply": "申请",
        "review": "审核",
        "approve": "审批",
        "archive": "归档"
    }

    # 流程流转顺序
    FLOW_SEQUENCE = ["apply", "review", "approve", "archive"]

    def __init__(self):
        self.blockchain = Blockchain()
        self.applications: Dict[str, dict] = {}
        self.templates: Dict[str, dict] = {}
        self._lock = threading.Lock()

    def create_template(self, name: str, fields: List[dict], owner: str, content: List[dict] = None) -> tuple:
        """创建模板"""
        with self._lock:
            template_id = str(uuid.uuid4())
            template = {
                "id": template_id,
                "name": name,
                "fields": fields,
                "content": content or [],
                "owner": owner,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            self.templates[template_id] = template
            return template_id, template

    def update_template(self, template_id: str, name: str = None, fields: List[dict] = None, content: List[dict] = None, owner: str = None) -> tuple:
        """更新模板"""
        with self._lock:
            if template_id not in self.templates:
                return None, "模板不存在"
            
            template = self.templates[template_id]
            
            if owner and template["owner"] != owner:
                return None, "无权限修改此模板"
            
            if name is not None:
                template["name"] = name
            
            if fields is not None:
                template["fields"] = fields
            
            if content is not None:
                template["content"] = content
            
            template["updated_at"] = datetime.now().isoformat()
            
            self.templates[template_id] = template
            return template_id, template

    def delete_template(self, template_id: str, owner: str) -> tuple:
        """删除模板"""
        with self._lock:
            if template_id not in self.templates:
                return False, "模板不存在"
            
            template = self.templates[template_id]
            if template["owner"] != owner:
                return False, "无权限删除此模板"
            
            del self.templates[template_id]
            return True, "模板删除成功"

    def get_template(self, template_id: str, owner: str) -> Optional[dict]:
        """获取模板（仅限所有者访问）"""
        with self._lock:
            if template_id not in self.templates:
                return None
            
            template = self.templates[template_id]
            if template["owner"] != owner:
                return None
            
            return template

    def get_user_templates(self, owner: str) -> List[dict]:
        """获取用户的所有模板"""
        with self._lock:
            return [template for template in self.templates.values() if template["owner"] == owner]

    def create_application(self, title: str, content: dict, applicant: str, template_id: str = None) -> dict:
        app_id = str(uuid.uuid4())
        application = {
            "id": app_id,
            "title": title,
            "content": content,
            "applicant": applicant,
            "template_id": template_id,
            "current_stage": "apply",
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "history": []
        }

        block_data = {
            "type": "application_created",
            "app_id": app_id,
            "stage": "apply",
            "operator": applicant,
            "title": title,
            "content": content,
            "template_id": template_id
        }

        def mine_and_add():
            block = self.blockchain.add_block(block_data)
            with self._lock:
                application["history"].append({
                    "stage": "apply",
                    "operator": applicant,
                    "timestamp": datetime.now().isoformat(),
                    "block_hash": block.hash,
                    "block_index": block.index
                })
                self.applications[app_id] = application
            return block

        return application, mine_and_add

    def process_application(self, app_id: str, operator: str, action: str, comment: str = "") -> tuple:
        with self._lock:
            if app_id not in self.applications:
                return None, "申请不存在"

            application = self.applications[app_id]
            current_stage = application["current_stage"]

            current_index = self.FLOW_SEQUENCE.index(current_stage)

            if action == "驳回":
                if current_index == 0:
                    return None, "申请阶段无法驳回"
                next_stage = self.FLOW_SEQUENCE[current_index - 1]
            else:
                if current_index >= len(self.FLOW_SEQUENCE) - 1:
                    return None, "流程已结束"
                next_stage = self.FLOW_SEQUENCE[current_index + 1]

            block_data = {
                "type": "application_processed",
                "app_id": app_id,
                "from_stage": current_stage,
                "to_stage": next_stage,
                "operator": operator,
                "action": action,
                "comment": comment
            }

            def mine_and_update():
                block = self.blockchain.add_block(block_data)
                with self._lock:
                    application["current_stage"] = next_stage
                    application["updated_at"] = datetime.now().isoformat()
                    application["history"].append({
                        "from_stage": current_stage,
                        "to_stage": next_stage,
                        "operator": operator,
                        "action": action,
                        "comment": comment,
                        "timestamp": datetime.now().isoformat(),
                        "block_hash": block.hash,
                        "block_index": block.index
                    })

                    if next_stage == "archive":
                        application["status"] = "completed"
                    else:
                        application["status"] = "pending"

                    self.applications[app_id] = application
                return block, application

            return mine_and_update, None

    def get_application(self, app_id: str) -> Optional[dict]:
        return self.applications.get(app_id)

    def get_all_applications(self) -> List[dict]:
        return list(self.applications.values())

    def get_user_applications(self, username: str) -> List[dict]:
        return [app for app in self.applications.values() if app["applicant"] == username]

    def get_pending_applications(self, stage: str) -> List[dict]:
        return [app for app in self.applications.values() 
                if app["current_stage"] == stage and app["status"] != "completed"]

    def get_blockchain_info(self) -> dict:
        return {
            "chain_length": len(self.blockchain.chain),
            "is_valid": self.blockchain.is_chain_valid(),
            "latest_block": {
                "index": self.blockchain.get_latest_block().index,
                "hash": self.blockchain.get_latest_block().hash,
                "timestamp": self.blockchain.get_latest_block().timestamp
            }
        }


# 单例模式
approval_system = GovernmentApprovalSystem()
