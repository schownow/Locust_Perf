import json
import logging
from http.client import HTTPConnection, HTTPResponse
from locust import HttpUser, SequentialTaskSet, task, between
from locust_plugins.csvreader import CSVReader

HTTPConnection.debuglevel = 1
HTTPResponse.debuglevel = 1
logging.basicConfig()
logging.getLogger()
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.INFO)
requests_log.propagate = True


users_details_reader = CSVReader("local_locust_scripts/testdata_companies.csv")


class SampleOrders(SequentialTaskSet):

    @task
    def on_start(self):
        self.test_data = next(users_details_reader)
        # Skip headers line
        if self.test_data[0] == "email":
            self.test_data = next(users_details_reader)
        if self.test_data:
            self.email = self.test_data[0]
            self.password = self.test_data[1]
            self.company_id = self.test_data[2]
            self.restaurant_latitude = self.test_data[3]
            self.restaurant_longitude = self.test_data[4]
            self.restaurant_id = self.test_data[5]
            self.restaurant_menu_id = self.test_data[6]

    @task
    def customer_login(self):
        response = self.client.post(name="R01_Customer_Login",
                                    url="/api/customer/login",
                                    json={
                                        "email": self.email,
                                        "password": self.password,
                                        "meta": {"marketplace": {"x_id": None, "id": "2"}},
                                    }, headers={"x-chownow": "True",
                                                "user-agent": "perf-locust"},
                                    )
        if response.status_code != 200:
            logging.error("Customer login failed - %s", response.content)
        else:
            self.user_data = json.loads(response.content)

    @task
    def customer_me(self):
        response = self.client.get(name="R02_Customer_Me",
                                   url="/api/customer/me",
                                   headers={"x-chownow": "True",
                                            "user-agent": "perf-locust"}
                                   )
        if response.status_code != 200:
            logging.error("customer Me is failed - %s", response.content)
        else:
            self.customer_data = json.loads(response.content)

    @task
    def company_id(self):
        response = self.client.get(name="R03_Company_Id",
                                   url=f"/api/company/{self.company_id}",
                                   headers={"x-chownow": "True",
                                            "user-agent": "perf-locust"}
                                   )
        if response.status_code != 200:
            logging.error("Company Id is Failed - %s", response.content)
        else:
            self.company_data = json.loads(response.content)
            # print("Response: ", self.company_data)
            # print("Company Id is success", response.status_code)

    @task
    def web_manifest(self):
        response = self.client.get(name="R04_Web_Manifest",
                                   url="/api/web/manifest",
                                   headers={"x-chownow": "True",
                                            "user-agent": "perf-locust"}
                                   )
        if response.status_code != 200:
            logging.error("Web Manifest is Failed - %s", response.content)

    @task
    def restaurant_id(self):
        response = self.client.get(name="R05_Restaurant_ID",
                                   url=f"/api/restaurant/{self.restaurant_id}",
                                   headers={"x-chownow": "True",
                                            "user-agent": "perf-locust"}
                                   )
        if response.status_code != 200:
            logging.error("Restaurant ID is Failed - %s", response.content)
        else:
            self.restaurant_data = json.loads(response.content)

    @task
    def get_restaurant_menu(self):
        response = self.client.get(name="R06_restaurant_menu",
                                   url=f"/api/restaurant/{self.restaurant_id}/menu",
                                   headers={"x-chownow": "True",
                                            "user-agent": "perf-locust"}
                                   )
        if response.status_code != 200:
            logging.error("Restaurant Menu is Failed - %s", response.content)
        else:
            menu = json.loads(response.content)
            self.menu_id = menu["id"]
            self.menu_datetime = menu["id"].split("_")[1]
            self.item_id = menu["menu_categories"][1]["items"][0]["id"]

    @task
    def get_menu_details(self):
        response = self.client.get(name="R07_menu_details",
                                   url=f"/api/restaurant/{self.restaurant_id}/menu/{self.menu_datetime}",
                                   headers={"x-chownow": "True",
                                            "user-agent": "perf-locust"}
                                   )
        if response.status_code != 200:
            logging.error("Restaurant Menu Details is Failed - %s", response.content)
        else:
            menu = json.loads(response.content)

    @task
    class PickupOrder(SequentialTaskSet):
        @task
        def validate_pickup_order(self):
            user_data = self.parent.user_data
            response = self.client.post(name="R08_Pickup_Order_Validate",
                                        url="/api/order/validate",
                                        json={
                                            "fulfill_method": "pickup",
                                            "items": [
                                                {
                                                    "id": f"{self.parent.item_id}",
                                                    "quantity": 1,
                                                    "recipient": None,
                                                    "special_instructions": None,
                                                    "client_id": "1653053484909000",
                                                    "modifier_categories": [],
                                                }
                                            ],
                                            "special_instructions": None,
                                            "tip": None,
                                            "promo_code": None,
                                            "restaurant_id": f"{self.parent.restaurant_id}",
                                            "when": None,
                                            "menu_id": f"{self.parent.menu_id}",
                                            "meta": {"channel": None, "client_type": "direct_web"},
                                            "customer": {
                                                "email": f"{user_data['email']}",
                                                "first_name": f"{user_data['first_name']}",
                                                "id": f"{user_data['id']}",
                                                "last_name": f"{user_data['last_name']}",
                                                "phone": {
                                                    "number": f"{user_data['phone']['number']}",
                                                    "id": f"{user_data['phone']['id']}",
                                                },
                                                "delivery": None,
                                            },
                                        },
                                        )
            if response.status_code != 200:
                logging.error("pickup order validate failed - %s", response.content)
            else:
                validated_order = json.loads(response.content)
                self.pickup_total_due = validated_order["total_due"]

        @task
        def place_pickup_order(self):
            user_data = self.parent.user_data
            billing_card = user_data["billing"]["cards"][0]
            response = self.client.post(name="R09_Pickup_Order",
                                        url="/api/order",
                                        json={
                                            "fulfill_method": "pickup",
                                            "items": [
                                                {
                                                    "id": f"{self.parent.item_id}",
                                                    "quantity": 1,
                                                    "recipient": None,
                                                    "special_instructions": None,
                                                    "client_id": "1653053484909000",
                                                    "modifier_categories": [],
                                                }
                                            ],
                                            "special_instructions": None,
                                            "tip": None,
                                            "promo_code": None,
                                            "restaurant_id": f"{self.parent.restaurant_id}",
                                            "when": None,
                                            "menu_id": f"{self.parent.menu_id}",
                                            "meta": {"channel": None, "client_type": "direct_web"},
                                            "customer": {
                                                "email": f"{user_data['email']}",
                                                "first_name": f"{user_data['first_name']}",
                                                "id": f"{user_data['id']}",
                                                "last_name": f"{user_data['last_name']}",
                                                "phone": {
                                                    "number": f"{user_data['phone']['number']}",
                                                    "id": f"{user_data['phone']['id']}",
                                                },
                                                "delivery": None,
                                                "billing": {
                                                    "card": {
                                                        "address": billing_card["address"],
                                                        "cvv": "123",
                                                        "number": None,
                                                        "exp_month": billing_card["exp_month"],
                                                        "exp_year": billing_card["exp_year"],
                                                        "id": billing_card["id"],
                                                        "is_visible": True,
                                                        "type": billing_card["type"],
                                                        "type_id": billing_card["type_id"],
                                                    }
                                                },
                                            },
                                            "validated_total": self.pickup_total_due,
                                        },
                                        )
            if response.status_code != 200:
                logging.error("place pickup order failed - %s", response.content)
            else:
                order = json.loads(response.content)
                self.pickup_order_id = order["id"]

        @task
        def get_pickup_order_by_id(self):
            self.client.get(name="R10_Get_pickup_order_id",
                            url=f"/api/order/{self.pickup_order_id}"
                            )

        @task
        def stop(self):
            self.interrupt()

    @task
    class DeliveryOrder(SequentialTaskSet):
        @task
        def validate_delivery_order(self):
            user_data = self.parent.user_data
            delivery_address = user_data["delivery"]["addresses"][0]
            response = self.client.post(name="R08_Delivery_Order_Validate",
                                        url="/api/order/validate",
                                        json={
                                            "fulfill_method": "delivery",
                                            "items": [
                                                {
                                                    "id": f"{self.parent.item_id}",
                                                    "quantity": 1,
                                                    "recipient": None,
                                                    "special_instructions": None,
                                                    "client_id": "1653053484909000",
                                                    "modifier_categories": [],
                                                }
                                            ],
                                            "special_instructions": None,
                                            "tip": None,
                                            "promo_code": None,
                                            "restaurant_id": f"{self.parent.restaurant_id}",
                                            "when": None,
                                            "menu_id": f"{self.parent.menu_id}",
                                            "meta": {"channel": None, "client_type": "direct_web"},
                                            "customer": {
                                                "email": f"{user_data['email']}",
                                                "first_name": f"{user_data['first_name']}",
                                                "id": f"{user_data['id']}",
                                                "last_name": f"{user_data['last_name']}",
                                                "phone": {
                                                    "number": f"{user_data['phone']['number']}",
                                                    "id": f"{user_data['phone']['id']}",
                                                },
                                                "delivery": {"address": delivery_address},
                                            },
                                        },
                                        )
            if response.status_code != 200:
                logging.error("delivery order validate failed - %s", response.content)
            else:
                validated_order = json.loads(response.content)
                self.delivery_total_due = validated_order["total_due"]

        @task
        def place_delivery_order(self):
            user_data = self.parent.user_data
            delivery_address = user_data["delivery"]["addresses"][0]
            billing_card = user_data["billing"]["cards"][0]
            response = self.client.post(name="R09_Delivery_Order",
                                        url="/api/order",
                                        json={
                                            "fulfill_method": "delivery",
                                            "items": [
                                                {
                                                    "id": f"{self.parent.item_id}",
                                                    "quantity": 1,
                                                    "recipient": None,
                                                    "special_instructions": None,
                                                    "client_id": "1653053484909000",
                                                    "modifier_categories": [],
                                                }
                                            ],
                                            "special_instructions": None,
                                            "tip": None,
                                            "promo_code": None,
                                            "restaurant_id": f"{self.parent.restaurant_id}",
                                            "when": None,
                                            "menu_id": f"{self.parent.menu_id}",
                                            "meta": {"channel": None, "client_type": "direct_web"},
                                            "customer": {
                                                "email": f"{user_data['email']}",
                                                "first_name": f"{user_data['first_name']}",
                                                "id": f"{user_data['id']}",
                                                "last_name": f"{user_data['last_name']}",
                                                "phone": {
                                                    "number": f"{user_data['phone']['number']}",
                                                    "id": f"{user_data['phone']['id']}",
                                                },
                                                "delivery": {"address": delivery_address},
                                                "billing": {
                                                    "card": {
                                                        "address": billing_card["address"],
                                                        "cvv": "123",
                                                        "number": None,
                                                        "exp_month": billing_card["exp_month"],
                                                        "exp_year": billing_card["exp_year"],
                                                        "id": billing_card["id"],
                                                        "is_visible": True,
                                                        "type": billing_card["type"],
                                                        "type_id": billing_card["type_id"],
                                                    }
                                                },
                                            },
                                            "validated_total": self.delivery_total_due,
                                        },
                                        )
            if response.status_code != 200:
                logging.error("place delivery order failed - %s", response.content)
            else:
                order = json.loads(response.content)
                self.delivery_order_id = order["id"]

        @task
        def get_delivery_order_by_id(self):
            self.client.get(name="R10_Get_delivery_order_id",
                            url=f"/api/order/{self.delivery_order_id}"
                            )

        @task
        def stop(self):
            self.interrupt()

    @task
    def logout(self):
        response = self.client.post(name="R11_Logout",
                                    url="/api/customer/logout"
                                    )
        if response.status_code != 200:
            logging.error("Logout failed - %s", response.content)


class MySeqTest(HttpUser):
    wait_time = between(3, 5)
    tasks = [SampleOrders]
