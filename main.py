from fastapi import FastAPI, status
from pydantic import BaseModel
from os import urandom

app = FastAPI()


class Cart:
    """Represents a checkout cart.
    """

    class CartSchema(BaseModel):

        class CartItem(BaseModel):
            id: int
            quantity: int

        items: list[CartItem] = []

    def __init__(self) -> None:
        """Constructor
        """

        self.products = dict()

    def addItem(self, id: int, num: int):
        """Adds the given item ID to the cart 'num' times.

        Args:
            id (int): Product ID.
            num (int): Quantity of items.
        """

        if id not in self.products:
            self.products[id] = 0

        self.products[id] += num

    def removeItem(self, id: int, num: int) -> bool:
        """Removes the given item ID from the cart 'num' times.

        Args:
            id (int): Product ID.
            num (int): Quantity to be removed.

        Raises:
            KeyError: Unknown product ID.
            ValueError: More is being removed than is present.

        Returns:
            bool: Task was successful or not.
        """
        if id not in self.products:
            raise KeyError

        if self.products[id] < num:
            raise ValueError

        self.products[id] -= num

        if self.products[id] == 0:
            del self.products[id]

    def getCart(self) -> CartSchema:
        """Returns the cart.

        Returns:
            CartSchema: Schema describing the JSON response.
        """
        response = self.CartSchema()
        for id, qty in self.products.items():
            response.items.append(self.CartSchema.CartItem(id=id, quantity=qty))

        return response


class Database:

    class ProductDatabaseSchema(BaseModel):

        class Product(BaseModel):
            id: int = -1
            name: str = "unknown"
            category: int = -1
            price: int = 0

        data: dict[int, Product] = {}

    class CategoryDatabaseSchema(BaseModel):

        class Category(BaseModel):
            id: int = -1
            name: str = "unknown"

        data: dict[int, Category] = {}

    def __init__(self) -> None:
        """Constructor
        """
        self.productDB = Database.ProductDatabaseSchema()
        self.categoryDB = Database.CategoryDatabaseSchema()

        self.connectToDatabase()

    def connectToDatabase(self):
        # Actual connection not needed
        # Connect to dummy database

        self.productDB = Database.ProductDatabaseSchema.parse_file("./products.json")

        self.categoryDB = Database.CategoryDatabaseSchema.parse_file("./categories.json")

    def newCategory(self, category: CategoryDatabaseSchema.Category) -> bool:
        """Creates a new category.

        Args:
            category (CategoryDatabaseSchema.Category): Details of the new Category.

        Returns:
            bool: Success or Failure.
        """
        if category.id in self.categoryDB.data.keys():
            return False

        self.categoryDB.data[category.id] = category

        return True

    def deleteCategory(self, category: id) -> bool:
        """Deletes an old category.

        Args:
            category (id): ID of the old Category.

        Returns:
            bool: Success or Failure.
        """
        if category in self.categoryDB.data.keys():
            del self.categoryDB.data[category]
            return True

        return False

    def getCatalogue(self):
        """Generates and returns the entire catalogue as a JSON.

        Returns:
            CatalogueSchema: The JSON schema of the catalogue.
        """

        class CatalogueSchema(BaseModel):
            data: dict[str, list[Database.ProductDatabaseSchema.Product]] = {}

        response = CatalogueSchema()
        response.data["unknown"] = []

        for id, category in self.categoryDB.data.items():
            response.data[category.name] = []

        for id, product in self.productDB.data.items():
            productCategory = self.categoryDB.data[
                product.category] if product.category in self.categoryDB.data.keys() else "unknown"
            response.data[productCategory.name].append(product)

        return response

    def getProduct(self, product: int) -> ProductDatabaseSchema.Product:
        """Returns the details of an individual product.

        Args:
            product (int): The ID of the product.

        Returns:
            ProductDatabaseSchema.Product: JSON description of the product.
        """
        response = self.ProductDatabaseSchema.Product

        if product in self.productDB.data.keys():
            response = self.productDB.data[product]

        return response

    def newProduct(self, product: ProductDatabaseSchema.Product) -> bool:
        """Adds a new product to the database.

        Args:
            product (ProductDatabaseSchema.Product): Description of the new product.

        Returns:
            bool: Success or Failure.
        """
        if product.id in self.productDB.data.keys():
            return False

        self.productDB.data[product.id] = product

        return True

    def updateProduct(self, product: ProductDatabaseSchema.Product) -> bool:
        """Updates an existing product.

        Args:
            product (ProductDatabaseSchema.Product): Updated details of the product. Note that the ID must be kept the same.

        Returns:
            bool: Success or Failure.
        """
        if product.id in self.productDB.data.keys():
            self.productDB.data[product.id] = product
            return True

        return False

    def deleteProduct(self, product: id) -> bool:
        """Deletes an already existing product.

        Args:
            product (id): ID of the product.

        Returns:
            bool: Success or Failure.
        """
        if product not in self.productDB.data.keys():
            return False

        del self.productDB.data[product]

        return True


class SessionHandler:

    class ValidationDatabase(BaseModel):

        class ValidationSchema(BaseModel):
            email: str
            password: str
            isAdmin: bool

        credentials: list[ValidationSchema] = []

    class PortalSchema(BaseModel):
        modes: dict[str, str]

    def __init__(self) -> None:
        self.userTokens = set()
        self.adminTokens = set()
        self.carts = {}
        self.database = self.ValidationDatabase.parse_file("./creds.json")
        self.paymentModes = self.PortalSchema.parse_file("./modes.json")

    def login(self, email: str, password: str) -> str:
        """Returns the session ID for the user after validating a login.

        Args:
            email (str): The given email for the login attempt.
            password (str): The given password for the login attempt.

        Returns:
            str: The session ID if successful, otherwise a blank.
        """
        for cred in self.database.credentials:
            sessionToken = urandom(8).hex()
            if cred.email == email and cred.password == password:
                if cred.isAdmin is False:
                    self.userTokens.add(sessionToken)
                else:
                    self.adminTokens.add(sessionToken)

                return sessionToken

        return ""


# Variables
sessions = SessionHandler()
db = Database()


#-----------------------------------------------------------
#!Routes
#-----------------------------------------------------------
@app.get("/")
async def root():
    return {"message": "Welcome to the Demo Marketplace"}


class LoginSchema(BaseModel):
    email: str
    password: str


@app.get("/login/{email}/{password}")
async def getSessionID(email: str, password: str):
    sessionID = sessions.login(email, password)
    if not sessionID:
        return {"Authentication Error": "Unknown credentials"}
    sessions.carts[sessionID] = Cart()
    return {"sessionID": sessionID}


@app.get("/catalogue")
async def catalogue():
    return db.getCatalogue()


@app.post("/new/product/{sessionID}")
async def newProduct(sessionID: str, product: Database.ProductDatabaseSchema.Product):
    if sessionID not in sessions.adminTokens:
        return {"Session Error": "Not Authorized"}
    db.newProduct(product=product)
    return db.getProduct(product=product.id)


@app.post("/update/product/{sessionID}")
async def updateProduct(sessionID: str, product: Database.ProductDatabaseSchema.Product):
    if sessionID not in sessions.adminTokens:
        return {"Session Error": "Not Authorized"}
    db.updateProduct(product=product)
    return db.getProduct(product=product.id)


@app.post("/delete/product/{product}/{sessionID}")
async def deleteProduct(product: int, sessionID: str):
    if sessionID not in sessions.adminTokens:
        return {"Session Error": "Not Authorized"}
    response = db.deleteProduct(product=product)
    return response


@app.post("/new/category/{sessionID}")
async def newCategory(sessionID: str, category: Database.CategoryDatabaseSchema.Category):
    if sessionID not in sessions.adminTokens:
        return {"Session Error": "Not Authorized"}
    response = db.newCategory(category=category)
    return response


@app.post("/delete/category/{category}/{sessionID}")
async def deleteCategory(category: int, sessionID: str):
    if sessionID not in sessions.adminTokens:
        return {"Session Error": "Not Authorized"}
    response = db.deleteCategory(category=category)
    return response


@app.get("/cart/get/{sessionID}")
async def cartGet(sessionID: str):
    if sessionID in sessions.carts.keys():
        return sessions.carts[sessionID].getCart()

    return {"Response": "User Not Found"}


class CartAddSchema(BaseModel):
    sessionID: str
    product: int
    quantity: int


@app.post("/cart/add/")
async def cartAdd(request: CartAddSchema):
    if request.sessionID not in sessions.userTokens:
        return {"Response": "User Not Found"}

    if request.quantity >= 0:
        sessions.carts[request.sessionID].addItem(request.product, request.quantity)
    else:
        sessions.carts[request.sessionID].removeItem(request.product, -request.quantity)

    return sessions.carts[request.sessionID].getCart()


@app.get("/cart/modes/{sessionID}")
async def cartModes(sessionID: str):
    if sessionID not in sessions.userTokens:
        return {"Session Error": "Not Authorized"}

    return {"Supported": sessions.paymentModes.modes}


@app.get("/cart/checkout/{mode}/{sessionID}")
async def cartCheckout(mode: str, sessionID: str):
    if sessionID not in sessions.userTokens:
        return {"Session Error": "Not Authorized"}

    if mode not in sessions.paymentModes.modes:
        return {
            "Payment Mode Error": "Unknown Payment Mode",
            "Known Payment Modes": sessions.paymentModes
        }

    netTotal = 0

    for item, qty in sessions.carts[sessionID].products.items():
        netTotal += db.getProduct(item).price * qty

    if netTotal == 0:
        return {"message": "No amount payable!"}

    return {
        "message":
            f"You will be shortly redirected to the portal for {sessions.paymentModes.modes[mode]} to make a payment of Rs. {netTotal}"
    }
