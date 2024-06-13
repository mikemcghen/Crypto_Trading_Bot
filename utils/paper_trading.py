import json
import os

class PaperTrading:
    def __init__(self, starting_balance=10000):
        self.balance = starting_balance
        self.portfolio = {}
        self.trade_log = []

    def buy(self, symbol, price, quantity):
        total_cost = price * quantity
        if self.balance >= total_cost:
            self.balance -= total_cost
            if symbol in self.portfolio:
                self.portfolio[symbol] += quantity
            else:
                self.portfolio[symbol] = quantity
            self.log_trade('buy', symbol, price, quantity)
        else:
            print("Insufficient balance to buy")

    def sell(self, symbol, price, quantity):
        if symbol in self.portfolio and self.portfolio[symbol] >= quantity:
            self.portfolio[symbol] -= quantity
            total_revenue = price * quantity
            self.balance += total_revenue
            self.log_trade('sell', symbol, price, quantity)
        else:
            print("Insufficient holdings to sell")

    def log_trade(self, action, symbol, price, quantity):
        trade = {
            'action': action,
            'symbol': symbol,
            'price': price,
            'quantity': quantity
        }
        self.trade_log.append(trade)
        self.save_log()

    def save_log(self):
        with open('paper_trading_log.json', 'w') as file:
            json.dump(self.trade_log, file, indent=4)

    def load_log(self):
        if os.path.exists('paper_trading_log.json'):
            with open('paper_trading_log.json', 'r') as file:
                self.trade_log = json.load(file)

# Example usage:
# paper_trading = PaperTrading()
# paper_trading.buy('BTC', 34000, 0.01)
# paper_trading.sell('BTC', 35000, 0.01)
