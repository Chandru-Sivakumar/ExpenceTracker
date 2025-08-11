// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ExpenseTracker {
    struct Expense {
        address user;
        uint256 amount;
        string category;
        string receiptHash;
        uint256 timestamp;
        bool verified;
    }
    
    mapping(address => Expense[]) public userExpenses;
    mapping(uint256 => Expense) public expenses;
    uint256 public expenseCount;
    
    event ExpenseAdded(address indexed user, uint256 indexed expenseId, uint256 amount, string category);
    event ExpenseVerified(uint256 indexed expenseId);
    
    function addExpense(
        uint256 _amount,
        string memory _category,
        string memory _receiptHash
    ) public returns (uint256) {
        expenseCount++;
        Expense memory newExpense = Expense({
            user: msg.sender,
            amount: _amount,
            category: _category,
            receiptHash: _receiptHash,
            timestamp: block.timestamp,
            verified: false
        });
        
        expenses[expenseCount] = newExpense;
        userExpenses[msg.sender].push(newExpense);
        
        emit ExpenseAdded(msg.sender, expenseCount, _amount, _category);
        return expenseCount;
    }
    
    function verifyExpense(uint256 _expenseId) public {
        require(_expenseId <= expenseCount, "Expense does not exist");
        require(!expenses[_expenseId].verified, "Expense already verified");
        
        expenses[_expenseId].verified = true;
        emit ExpenseVerified(_expenseId);
    }
    
    function getUserExpenses(address _user) public view returns (Expense[] memory) {
        return userExpenses[_user];
    }
    
    function getExpense(uint256 _expenseId) public view returns (Expense memory) {
        require(_expenseId <= expenseCount, "Expense does not exist");
        return expenses[_expenseId];
    }
} 