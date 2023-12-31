source ../global_settings

echo -e "\n========================="
echo "Bluetooth ble stop discovery"

${CURL_APP} --location --request PUT ${URL}/api/v2/bluetooth/${BT_CONTROLLER} \
    --header "Content-Type: application/json" \
    -b cookie -c cookie --insecure\
    --data '{
        "command": "bleStopDiscovery"
        }' \
    | ${JQ_APP}

