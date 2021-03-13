## Contract Watcher Runner

Tool for running ipld-eth-indexer, ipld-eth-server, eth-header-sync and eth-contract-watcher in docker-compose, 
deploy smart contract and automatically configure config

### Prerequisites

* docker
* docker-compose
* python v3

### Upgrade from previous version

Remove existing images and volumes:
```
docker-compose down -v
```

### Setup

* Initialize and activate Python venv:
```
python3 -m venv ./venv
. ./venv/bin/activate
```

* Install dependency

```
pip install -r requirements.txt
```

* Put your solidity smart contract to `contracts` folder.
* Copy `config.example.toml` to `config.toml` and edit it if necessary
```
cp config.example.toml config.toml
```

* Run script

```
python main.py contracts
```

It can takes around 2 minutes to spin up geth node and run all services.

You will see messages like this:

```
Copying contract "Test.sol" to dapptool container ...
Coinbase is 0xfedb5c1d17eba6182a69ab2156ee4c13adf854e4
Building contracts...
Deploying contract Test...
Contract Test address is 0xA18AFFF4D4f753De1bA3858b7A179eE9165C72A5

```

### Call Smart Contract function to trigger event

* Connect to dapptools container

```
docker-compose exec dapptools sh
```

* Save coinbase address and contract address

You can obtain these addresses from the output of the previous command (python main.py contracts).

For example:
```
export ETH_FROM="0xfedb5c1d17eba6182a69ab2156ee4c13adf854e4"
export CONTRACT_ADDRESS="0xA18AFFF4D4f753De1bA3858b7A179eE9165C72A5"
```

* Call smart contract function

```
ETH_RPC_ACCOUNTS=1 seth send --gas 0xffffff $CONTRACT_ADDRESS 'setMessage(string)' '"abc1"'
```

You will see something similar to 

```
seth-send: Published transaction with 100 bytes of calldata.
seth-send: 0x307d42410eb5822f881611cb6980cc062e02fa3630cb60b98f62f5eee64a091a
seth-send: Waiting for transaction receipt...
seth-send: Transaction included in block 4.
```

* Call function a couple more times with another parameter:

```
ETH_RPC_ACCOUNTS=1 seth send --gas 0xffffff $CONTRACT_ADDRESS 'setMessage(string)' '"abc2"'
ETH_RPC_ACCOUNTS=1 seth send --gas 0xffffff $CONTRACT_ADDRESS 'setMessage(string)' '"abc3"'

```

* Get postgraphile service: open in browser http://127.0.0.1:5101/graphiql and perform graphql query


### Query data from watcher graphql

**Note:** you need to restart `eth-watcher-ts` service first. Because postgraphile cache database schema. 

```
docker-compose restart eth-watcher-ts
```

Open in browser `http://127.0.0.1:5101/graphiql` GraphQL interface from eth-watcher-ts and execute query:

```
query MyQuery {
  allContractId1EventId1S {
    nodes {
      contractId
      dataMessage
      eventId
      id
      mhKey
    }
  }
}
``` 

and you will get all contract event data