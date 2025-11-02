# Compendium of Python Coding Best Practices
*Inspired by the ArjanCodes YouTube Channel*

## Introduction

This compendium serves as an instructional guide to writing clean, maintainable, and scalable Python code. It synthesizes key software design principles, common design patterns, and frequently-encountered anti-patterns, drawing heavily from the educational content of the ArjanCodes YouTube channel. The goal is to provide a comprehensive resource with clear "bad code vs. good code" examples, making it easily digestible for developers and AI agents tasked with code analysis and correction.

---

## 1. SOLID Principles

SOLID is an acronym for five core design principles that are fundamental to creating robust and maintainable object-oriented software.

### 1.1. Single Responsibility Principle (SRP)
**Principle: A class should have one, and only one, reason to change.**

This means a class should have a single, well-defined responsibility.

**Bad Code Example:**
The `Order` class is responsible for managing items, calculating totals, and processing payments. This violates SRP because changes to payment logic, calculation logic, or item management would all require modifying this one class.

```python
class Order:
    def __init__(self):
        self.items = []
        self.status = "open"

    def add_item(self, item_name, quantity, price):
        self.items.append({"name": item_name, "quantity": quantity, "price": price})

    def calculate_total(self):
        return sum(item['quantity'] * item['price'] for item in self.items)

    def process_payment(self, payment_type, security_code):
        if payment_type == "debit":
            print("Processing debit payment...")
            print(f"Verifying security code: {security_code}")
            self.status = "paid"
        elif payment_type == "credit":
            print("Processing credit payment...")
            print(f"Verifying security code: {security_code}")
            self.status = "paid"
```

**Good Code Example:**
Responsibilities are segregated into distinct classes. `Order` manages items, while `PaymentProcessor` handles payments. This adheres to SRP.

```python
class Order:
    def __init__(self):
        self.items = []
        self.status = "open"

    def add_item(self, item_name, quantity, price):
        self.items.append({"name": item_name, "quantity": quantity, "price": price})

    def calculate_total(self):
        return sum(item['quantity'] * item['price'] for item in self.items)

class PaymentProcessor:
    def process_debit(self, order, security_code):
        print("Processing debit payment...")
        print(f"Verifying security code: {security_code}")
        order.status = "paid"

    def process_credit(self, order, security_code):
        print("Processing credit payment...")
        print(f"Verifying security code: {security_code}")
        order.status = "paid"
```

### 1.2. Open/Closed Principle (OCP)
**Principle: Software entities should be open for extension, but closed for modification.**

You should be able to add new functionality without changing existing code.

**Bad Code Example:**
The `PaymentProcessor` class must be modified each time a new payment method is introduced. The `if-elif` chain is a strong indicator of an OCP violation.

```python
class PaymentProcessor:
    def process_payment(self, payment_method, order):
        if payment_method == "debit":
            # Debit payment logic...
            order.status = "paid"
        elif payment_method == "credit":
            # Credit payment logic...
            order.status = "paid"
        elif payment_method == "paypal":
            # PayPal payment logic...
            order.status = "paid"
```

**Good Code Example:**
We introduce a `PaymentMethod` abstract base class (an interface). New payment methods can be added by creating new classes that implement this interface, without modifying the `PaymentProcessor`. The system is now open to new payment types but closed to modifications of its core logic.

```python
from abc import ABC, abstractmethod

class PaymentMethod(ABC):
    @abstractmethod
    def process(self, amount):
        pass

class DebitPayment(PaymentMethod):
    def process(self, amount):
        print(f"Processing ${amount} with Debit.")

class PayPalPayment(PaymentMethod):
    def process(self, amount):
        print(f"Processing ${amount} with PayPal.")

class PaymentProcessor:
    def process_payment(self, payment_method: PaymentMethod, amount):
        payment_method.process(amount)
```

### 1.3. Liskov Substitution Principle (LSP)
**Principle: Subtypes must be substitutable for their base types without altering the correctness of the program.**

A subclass should behave in the same way as its parent class, so it doesn't produce unexpected results.

**Bad Code Example:**
A `Square` inherits from `Rectangle`. However, setting the width of a `Square` also changes its height, which violates the expected behavior of a `Rectangle` (where width and height can be set independently). This could break a function that expects a `Rectangle` but receives a `Square`.

```python
class Rectangle:
    def __init__(self, width, height):
        self._width = width
        self._height = height

    def set_width(self, width):
        self._width = width

    def set_height(self, height):
        self._height = height

    def get_area(self):
        return self._width * self._height

class Square(Rectangle):
    def set_width(self, width):
        self._width = width
        self._height = width

    def set_height(self, height):
        self._width = height
        self._height = height
```

**Good Code Example:**
A better design is to have a generic `Shape` base class. `Rectangle` and `Square` are distinct shapes that implement the `Shape` interface. They are no longer in a parent-child relationship that violates behavior, thus adhering to LSP.

```python
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def get_area(self):
        pass

class Rectangle(Shape):
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def get_area(self):
        return self.width * self.height

class Square(Shape):
    def __init__(self, side):
        self.side = side

    def get_area(self):
        return self.side * self.side
```

### 1.4. Interface Segregation Principle (ISP)
**Principle: Clients should not be forced to depend on interfaces they do not use.**

Create smaller, more specific interfaces rather than one large, general-purpose one.

**Bad Code Example:**
A `Worker` interface includes an `eat` method. A `Robot` class is forced to implement `eat`, even though it's irrelevant and raises an error. The `Robot` is forced to depend on a method it does not use.

```python
from abc import ABC, abstractmethod

class Worker(ABC):
    @abstractmethod
    def work(self):
        pass

    @abstractmethod
    def eat(self):
        pass

class Human(Worker):
    def work(self):
        print("Human working...")
    def eat(self):
        print("Human eating...")

class Robot(Worker):
    def work(self):
        print("Robot working...")
    def eat(self):
        raise NotImplementedError("Robots don't eat!")
```

**Good Code Example:**
The interfaces are segregated by capability. `Workable` and `Eatable` are separate. `Human` implements both, while `Robot` only implements `Workable`, adhering to ISP.

```python
from abc import ABC, abstractmethod

class Workable(ABC):
    @abstractmethod
    def work(self):
        pass

class Eatable(ABC):
    @abstractmethod
    def eat(self):
        pass

class Human(Workable, Eatable):
    def work(self):
        print("Human working...")
    def eat(self):
        print("Human eating...")

class Robot(Workable):
    def work(self):
        print("Robot working...")
```

### 1.5. Dependency Inversion Principle (DIP)
**Principle: High-level modules should not depend on low-level modules. Both should depend on abstractions.**

This principle helps to decouple components.

**Bad Code Example:**
The high-level `Switch` class directly depends on the low-level `LightBulb` class. This creates tight coupling. If we want the switch to control a `Fan`, we must modify the `Switch` class.

```python
class LightBulb:
    def turn_on(self):
        print("LightBulb is ON")
    def turn_off(self):
        print("LightBulb is OFF")

class Switch:
    def __init__(self):
        self.light_bulb = LightBulb()
        self.is_on = False

    def operate(self):
        if self.is_on:
            self.light_bulb.turn_off()
            self.is_on = False
        else:
            self.light_bulb.turn_on()
            self.is_on = True
```

**Good Code Example:**
We introduce a `Switchable` abstraction (interface). The `Switch` now depends on this abstraction, not the concrete `LightBulb`. This inverts the dependency and allows the `Switch` to control any device that implements the `Switchable` interface, adhering to DIP.

```python
from abc import ABC, abstractmethod

class Switchable(ABC):
    @abstractmethod
    def turn_on(self):
        pass
    @abstractmethod
    def turn_off(self):
        pass

class LightBulb(Switchable):
    def turn_on(self):
        print("LightBulb is ON")
    def turn_off(self):
        print("LightBulb is OFF")

class Fan(Switchable):
    def turn_on(self):
        print("Fan is ON")
    def turn_off(self):
        print("Fan is OFF")

class Switch:
    def __init__(self, device: Switchable):
        self.device = device
        self.is_on = False

    def operate(self):
        if self.is_on:
            self.device.turn_off()
            self.is_on = False
        else:
            self.device.turn_on()
            self.is_on = True
```

---

## 2. Design Patterns

Design patterns are reusable, well-documented solutions to commonly occurring problems within a given context in software design.

### 2.1. Strategy Pattern
**Purpose:** Defines a family of algorithms, encapsulates each one, and makes them interchangeable. This allows the algorithm to vary independently from the clients that use it.

**Bad Code Example:**
The `OrderProcessor` uses a large `if/elif/else` block to select a payment processing algorithm. Adding a new payment method requires modifying this class, violating the Open/Closed Principle.

```python
class OrderProcessor:
    def process_order(self, payment_method, amount):
        if payment_method == "credit_card":
            print(f"Processing ${amount} with Credit Card...")
            # Complex credit card logic...
        elif payment_method == "paypal":
            print(f"Processing ${amount} with PayPal...")
            # Complex PayPal logic...
```

**Good Code Example:**
We define a `PaymentStrategy` interface and create concrete strategy classes for each payment method. The `Order` class is configured with a strategy object at runtime and delegates the payment processing to it. This decouples the algorithm from the client.

```python
from abc import ABC, abstractmethod

class PaymentStrategy(ABC):
    @abstractmethod
    def pay(self, amount):
        pass

class CreditCardPayment(PaymentStrategy):
    def pay(self, amount):
        print(f"Processing ${amount} with Credit Card.")

class PayPalPayment(PaymentStrategy):
    def pay(self, amount):
        print(f"Processing ${amount} with PayPal.")

class Order:
    def __init__(self, amount, payment_strategy: PaymentStrategy):
        self.amount = amount
        self.payment_strategy = payment_strategy

    def checkout(self):
        self.payment_strategy.pay(self.amount)
```

### 2.2. Builder Pattern
**Purpose:** Separates the construction of a complex object from its representation, allowing the same construction process to create different representations. It's ideal for objects with many optional parameters.

**Bad Code Example:**
The `Computer` class has a constructor with numerous optional parameters. This is hard to read, prone to errors (e.g., incorrect parameter order), and inflexible.

```python
class Computer:
    def __init__(self, cpu, ram, storage, gpu=None, os=None):
        self.cpu = cpu
        self.ram = ram
        self.storage = storage
        self.gpu = gpu
        self.os = os
    # ...
```

**Good Code Example:**
The `ComputerBuilder` class provides a fluent API to construct the `Computer` object step-by-step. This is more readable and less error-prone. The construction logic is separated from the `Computer`'s representation.

```python
class Computer:
    def __init__(self):
        self.cpu = None
        self.ram = None
        self.storage = None
        self.gpu = None
        self.os = None

    def __str__(self):
        return f"CPU: {self.cpu}, RAM: {self.ram}, Storage: {self.storage}, GPU: {self.gpu}, OS: {self.os}"

class ComputerBuilder:
    def __init__(self):
        self.computer = Computer()

    def set_cpu(self, cpu):
        self.computer.cpu = cpu
        return self

    def set_ram(self, ram):
        self.computer.ram = ram
        return self

    def set_storage(self, storage):
        self.computer.storage = storage
        return self

    def set_gpu(self, gpu):
        self.computer.gpu = gpu
        return self

    def build(self):
        return self.computer

# Usage:
builder = ComputerBuilder()
gaming_pc = builder.set_cpu("Intel i9").set_ram("32GB").set_storage("2TB SSD").set_gpu("Nvidia RTX 4090").build()
print(gaming_pc)
```

### 2.3. Factory Method Pattern
**Purpose:** Defines an interface for creating an object, but lets subclasses decide which class to instantiate.

**Bad Code Example:**
The client code directly instantiates concrete classes (`Dog`, `Cat`). This creates tight coupling. If a new animal type is added, the client code must be modified.

```python
class Dog:
    def speak(self):
        return "Woof!"

class Cat:
    def speak(self):
        return "Meow!"

# Client code
animal_type = "dog"
if animal_type == "dog":
    animal = Dog()
elif animal_type == "cat":
    animal = Cat()

print(animal.speak())
```

**Good Code Example:**
An `AnimalFactory` provides a `create_animal` method. Subclasses can override this method to produce different types of animals. The client code is now decoupled from the concrete animal classes.

```python
from abc import ABC, abstractmethod

class Animal(ABC):
    @abstractmethod
    def speak(self):
        pass

class Dog(Animal):
    def speak(self):
        return "Woof!"

class Cat(Animal):
    def speak(self):
        return "Meow!"

class AnimalFactory:
    def create_animal(self, animal_type):
        if animal_type == "dog":
            return Dog()
        elif animal_type == "cat":
            return Cat()
        raise ValueError("Unknown animal type")

# Client code
factory = AnimalFactory()
animal = factory.create_animal("cat")
print(animal.speak())
```

### 2.4. State Pattern
**Purpose:** Allows an object to alter its behavior when its internal state changes. The object will appear to change its class.

**Bad Code Example:**
The `TrafficLight` uses `if/elif` statements to handle state transitions. As more states are added, this method becomes complex and difficult to maintain.

```python
class TrafficLight:
    def __init__(self):
        self.state = "red"

    def change(self):
        if self.state == "red":
            self.state = "green"
            print("Light is now GREEN")
        elif self.state == "green":
            self.state = "yellow"
            print("Light is now YELLOW")
        elif self.state == "yellow":
            self.state = "red"
            print("Light is now RED")
```

**Good Code Example:**
Each state is encapsulated in its own class (`RedState`, `GreenState`). The `TrafficLight` (context) delegates the state transition behavior to its current state object. This design is clean, adheres to the Single Responsibility and Open/Closed principles, and is easy to extend.

```python
from abc import ABC, abstractmethod

class TrafficLightState(ABC):
    @abstractmethod
    def handle(self, light):
        pass

class RedState(TrafficLightState):
    def handle(self, light):
        print("Light is now GREEN")
        light.set_state(GreenState())

class GreenState(TrafficLightState):
    def handle(self, light):
        print("Light is now YELLOW")
        light.set_state(YellowState())

class YellowState(TrafficLightState):
    def handle(self, light):
        print("Light is now RED")
        light.set_state(RedState())

class TrafficLight:
    def __init__(self):
        self._state = RedState()

    def set_state(self, state):
        self._state = state

    def change(self):
        self._state.handle(self)
```

---

## 3. Python Anti-Patterns & Code Smells

Anti-patterns are common responses to recurring problems that are usually ineffective and risk being counterproductive.

**1. Using Exceptions for Control Flow**
*   **Problem:** Relying on `try-except` blocks for normal program logic instead of `if-else` conditionals. This is less readable and performant. Exceptions should be for exceptional events.
*   **Bad Code:**
    ```python
    try:
        value = my_dict[key]
    except KeyError:
        value = "default"
    ```
*   **Good Code:**
    ```python
    value = my_dict.get(key, "default")
    ```

**2. Using Classes with Only Static Methods**
*   **Problem:** In Python, modules are namespaces. Creating a class solely to hold static methods is often unnecessary boilerplate. Grouping related functions in a module is more Pythonic.
*   **Bad Code:**
    ```python
    class StringUtils:
        @staticmethod
        def is_palindrome(s):
            return s == s[::-1]
    # Usage: StringUtils.is_palindrome("racecar")
    ```
*   **Good Code:**
    ```python
    # string_utils.py
    def is_palindrome(s):
        return s == s[::-1]
    # Usage: from string_utils import is_palindrome; is_palindrome("racecar")
    ```

**3. Hardcoded Values ("Magic Numbers")**
*   **Problem:** Scattering literal values (numbers, strings) throughout the code makes it hard to understand and maintain.
*   **Bad Code:**
    ```python
    if order_total > 100:
        shipping_cost = 0  # Free shipping
    ```
*   **Good Code:**
    ```python
    FREE_SHIPPING_THRESHOLD = 100
    if order_total > FREE_SHIPPING_THRESHOLD:
        shipping_cost = 0
    ```

**4. Over-engineering with Unnecessary Design Patterns**
*   **Problem:** Applying complex design patterns when a simpler solution would suffice. Start simple and introduce patterns only when complexity justifies it.

**5. Wildcard Imports (`from module import *`)**
*   **Problem:** Pollutes the global namespace, making it unclear where functions or variables originate from and increasing the risk of name conflicts.
*   **Bad Code:**
    ```python
    from math import *
    from cmath import * # Both have sqrt, which one is used?
    print(sqrt(-1))
    ```
*   **Good Code:**
    ```python
    import math
    import cmath
    print(cmath.sqrt(-1))
    ```

**6. Not Using Abstraction**
*   **Problem:** Tightly coupling code to concrete implementations makes it rigid and difficult to test or change. Use abstractions (`ABC`, `Protocol`) to define interfaces and decouple components.