## Contract Watcher Runner

Tool for running ipld-eth-indexer, ipld-eth-server, eth-header-sync and eth-contract-watcher in docker-compose, 
deploy smart contract and automatically configure config

### Prerequisites

* docker
* docker-compose
* python v3

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
Copy `config.example.toml` to `config.toml` and edit it if necessary

* Run script

```
python main.py contracts
```

It can takes around 2 minutes to spin up geth node and run all services.