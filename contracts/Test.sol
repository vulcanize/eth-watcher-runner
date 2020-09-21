pragma solidity ^0.6.7;

contract Test {
    string public message = "hello world";
    event MessageChanged(string message);

    function setMessage(string calldata _message) external {
        message = _message;
        emit MessageChanged(message);
    }

    function getMessage() public view returns (string memory _message) {
        return message;
    }
}