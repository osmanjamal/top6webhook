# Replace XXXXX with your actual webhook key
$WEBHOOK_KEY = "WebhookReceived:XXXXX"
$WEBHOOK_URL = "http://localhost:5000/webhook"

# Test 1: Basic Buy Order
Write-Host "Testing Buy Order..."
$buyOrder = @{
    key = $WEBHOOK_KEY
    symbol = "BTCUSDT"
    side = "buy"
    amount = 0.001
} | ConvertTo-Json

Invoke-RestMethod -Uri $WEBHOOK_URL -Method Post -Body $buyOrder -ContentType "application/json"
Start-Sleep -Seconds 2

# Test 2: Sell Order
Write-Host "Testing Sell Order..."
$sellOrder = @{
    key = $WEBHOOK_KEY
    symbol = "ETHUSDT"
    side = "sell"
    amount = 0.1
} | ConvertTo-Json

Invoke-RestMethod -Uri $WEBHOOK_URL -Method Post -Body $sellOrder -ContentType "application/json"
Start-Sleep -Seconds 2

# Test 3: Order with Stop Loss and Take Profit
Write-Host "Testing Order with SL/TP..."
$sltpOrder = @{
    key = $WEBHOOK_KEY
    symbol = "BTCUSDT"
    side = "buy"
    amount = 0.001
    stopLoss = 43000
    takeProfit = 45000
} | ConvertTo-Json

Invoke-RestMethod -Uri $WEBHOOK_URL -Method Post -Body $sltpOrder -ContentType "application/json"