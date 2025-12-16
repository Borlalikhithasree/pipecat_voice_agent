#!/bin/bash

curl -X POST http://localhost:7860/start-call \
  -H "Content-Type: application/json" \
  -d '{
        "to": "+917731862569",
        "from": "+18573679132",
        "campaign_id": "loan_recovery",
        "customer_id": "demo_user"
      }'
