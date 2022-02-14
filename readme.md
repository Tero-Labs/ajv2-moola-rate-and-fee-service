# Moola Oracle Dependent Data From Smart Contract
Serve Moola V2 oracle dependent, rate and fee related Data through REST Api directly from blockchain for `alfajores` deployment.



## API documentation


### API overview

|API Endpoints                    |Query Params                            |Description                                                               |
|---------------------------------|----------------------------------------|--------------------------------------------------------------------------|
|/get/getRateInUsd                |coin_name                               |Get the price of the specified coin in USD rate                           |
|/get/getLiquidationPrice         |userPublicKey                           |Get liquidation price for each collteral assets                           |
|get/getFee                       |userPublicKey,activityType,currency{Opt}|Get associated fee for doing the specific activity with the specific asset|

### API response format

1.  `/get/getRateInUsd`
```
'status',

'dateTime',

'coinName',

'RateInUsd',
```


2.  `/get/getLiquidationPrice`
```
'status',

'dateTime',

'data':
    'collateral',
    'collateralAssets': [
        {
            'currency',
            'liquidationPrice',
            'currentPrice',
            'priceCurrency'
        },
        ...
    ]
```


3.  `/get/getFee`
```
'status',

'dateTime',

'currency',

'activity',

'amount',

'securityFee'
```