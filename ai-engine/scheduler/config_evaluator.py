import boto3
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

config_client = boto3.client("config")

CONFIG_RULES = [
    "adb-no-unrestricted-ssh",
    "adb-s3-no-public-access",
    "adb-no-root-access-key",
    "adb-ebs-encrypted",
    "adb-cloudtrail-enabled"
]


def handler(event, context):
    timestamp = datetime.now(timezone.utc).isoformat()
    logger.info(f"Config evaluator triggered at {timestamp}")
    logger.info(f"Evaluating all {len(CONFIG_RULES)} rules in single call")

    try:
        # Single API call for all rules — much faster, no rate limit issues
        config_client.start_config_rules_evaluation(
            ConfigRuleNames=CONFIG_RULES
        )
        logger.info(f"All {len(CONFIG_RULES)} rules triggered successfully")

        return {
            "statusCode": 200,
            "timestamp":  timestamp,
            "summary":    f"{len(CONFIG_RULES)}/{len(CONFIG_RULES)} rules triggered",
            "results": [
                {"rule": r, "status": "triggered", "time": timestamp}
                for r in CONFIG_RULES
            ]
        }

    except Exception as e:
        logger.error(f"Evaluation failed: {str(e)}")
        return {
            "statusCode": 500,
            "timestamp":  timestamp,
            "error":      str(e),
            "summary":    "0/5 rules triggered"
        }