import random

class MockAS7343:
    def read(self):
        return {
            "F1": random.randint(900, 1300),
            "F2": random.randint(1200, 1700),
            "FZ": random.randint(1500, 2200),
            "F3": random.randint(1800, 2600),
            "F4": random.randint(2500, 3500),
            "FY": random.randint(3000, 4200),
            "F5": random.randint(2800, 3900),
            "FXL": random.randint(2300, 3300),
            "F6": random.randint(1800, 2800),
            "F7": random.randint(1200, 2200),
            "F8": random.randint(800, 1600),
            "NIR": random.randint(200, 700)
        }
