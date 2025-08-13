from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict

from sqlalchemy import Integer, String, Float, Boolean
from sqlalchemy.orm import Session, Mapped, mapped_column

from litestar import Litestar, get, post, put, patch, delete
from litestar.controller import Controller
from litestar.di import Provide
from litestar.exceptions import ValidationException
from litestar.plugins.sqlalchemy import SQLAlchemyInitPlugin, SQLAlchemySyncConfig, base, repository, service


class BaseSchema(BaseModel):
    """
    Base schema with ORM mode enabled
    """
    model_config = ConfigDict(from_attributes=True)


class MotorcycleModel(base.BigIntBase):
    """
    SQLAlchemy model for a motorcycle
    """
    __tablename__ = "motorcycle"
    __table_args__ = {"schema": "vehicle"}

    vin: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    motorcycle_type: Mapped[str] = mapped_column(String)
    odometer_value: Mapped[float] = mapped_column(Float, nullable=False)
    odometer_unit: Mapped[str] = mapped_column(String, nullable=False)
    is_electric: Mapped[bool] = mapped_column(Boolean, nullable=False)
    number_of_seats: Mapped[int] = mapped_column(Integer, nullable=False)


class MotorcycleResponse(BaseSchema):
    """
    Response schema for a motorcycle
    """
    id: int
    vin: str
    motorcycle_type: str
    odometer_value: float
    odometer_unit: str
    is_electric: bool
    number_of_seats: int


class MotorcycleCreate(BaseSchema):
    """
    Schema for creating motorcycles
    """
    vin: str
    motorcycle_type: str
    odometer_value: float
    odometer_unit: str
    is_electric: bool
    number_of_seats: int


class MotorcycleUpdate(BaseSchema):
    """
    Schema for creating motorcycles
    """
    vin: str | None = None
    motorcycle_type: str | None = None
    odometer_value: float | None = None
    odometer_unit: str | None = None
    is_electric: bool | None = None
    number_of_seats: int | None = None


class MotorcycleRepository(repository.SQLAlchemySyncRepository[MotorcycleModel]):
    """
    Repository for MotorcycleModel operations.
    """
    model_type = MotorcycleModel

    def list_motorcycles(self) -> List[MotorcycleModel]:
        """
        List all motorcycle entries.

        :return: MotorcycleModel - List of MotorcycleModel instances, ordered by VIN in descending order.
        """
        return self.list(order_by=(MotorcycleModel.vin, False))

    def get_motorcycle_by_vin(self, vin: str) -> MotorcycleModel:
        """
        Retrieve a motorcycle by its VIN.

        :param vin: str - The VIN of the motorcycle to retrieve.
        :return: MotorcycleModel - The motorcycle instance with the specified VIN.
        """
        return self.get_one(vin=vin)

    def create_motorcycle(self, data: MotorcycleModel) -> MotorcycleModel:
        """
        Create a new motorcycle entry.

        :param data: MotorcycleModel - The motorcycle data to create.
        :return: MotorcycleModel - The created motorcycle instance.
        """
        return self.add(data=data, auto_refresh=True, auto_commit=True)

    def update_motorcycle(self, data: MotorcycleModel) -> MotorcycleModel:
        """
        Update an existing motorcycle entry.

        :param data: MotorcycleModel - The motorcycle data to update.
        :return: MotorcycleModel - The updated motorcycle instance.
        """
        existing_db_obj = self.get_one(vin=data.vin)
        data.id = existing_db_obj.id  # Update the ID to match the existing record
        return self.update(data=data, auto_refresh=True, auto_commit=True)

    def delete_motorcycle_by_vin(self, vin: str) -> None:
        """
        Delete a motorcycle entry by its VIN.

        :param vin: str - The VIN of the motorcycle to delete.
        :return: None
        """
        db_obj = self.get_one(vin=vin)
        self.delete(item_id=db_obj.id, auto_commit=True)


class MotorcycleService(service.SQLAlchemySyncService[MotorcycleModel, MotorcycleRepository]):
    """
    Service for MotorcycleModel operations.
    """
    repository_type = MotorcycleRepository

    def list_motorcycles(self) -> List[MotorcycleResponse]:
        """
        Get all Motorcycle entries and convert them to response models.

        :return: List[MotorcycleResponse] - List of MotorcycleResponse instances.
        """
        db_objs = self.repository.list_motorcycles()
        return [MotorcycleResponse.model_validate(obj) for obj in db_objs]

    def get_motorcycle_by_vin(self, vin: str) -> MotorcycleResponse:
        """
        Get a specific motorcycle by its VIN and convert it to a response model.

        :param vin: str - The VIN of the motorcycle to retrieve.
        :return: MotorcycleResponse - The motorcycle instance with the specified VIN.
        """
        db_obj = self.repository.get_motorcycle_by_vin(vin=vin)
        return MotorcycleResponse.model_validate(db_obj)

    def create_motorcycle(self, data: MotorcycleCreate) -> MotorcycleResponse:
        """
        Create a new motorcycle entry and return the created instance as a response model.

        :param data: MotorcycleCreate - The new Motorcycle entry data.
        :return: MotorcycleResponse - The created Motorcycle instance.
        """
        db_data = MotorcycleModel(**data.model_dump())
        db_obj = self.repository.create_motorcycle(data=db_data)
        return MotorcycleResponse.model_validate(db_obj)

    def update_motorcycle(self, vin: str, data: MotorcycleCreate | MotorcycleUpdate) -> MotorcycleResponse:
        """
        Update an existing motorcycle entry and return the updated instance as a response model.

        :param vin: str - The VIN of the motorcycle to update.
        :param data: MotorcycleCreate | MotorcycleUpdate - The data to update with.
        :return: MotorcycleResponse - The updated Motorcycle instance.
        """
        if vin != data.vin:
            raise ValidationException("provided data does not match VIN in path.")

        # If data is MotorcycleCreate it must be a PUT operation, since MotorcycleUpdate doesn't allow optional fields.
        # Otherwise, it must be a PATCH operation, since MotorcycleUpdate does allow optional fields.
        data_dict = data.model_dump(exclude_unset=True) if isinstance(data, MotorcycleUpdate) else data.model_dump()

        db_data = MotorcycleModel(**data_dict)
        db_obj = self.repository.update_motorcycle(data=db_data)
        return MotorcycleResponse.model_validate(db_obj)


    def delete_motorcycle_by_vin(self, vin: str) -> None:
        """
        Delete a motorcycle entry by its VIN.

        :param vin: str - The VIN of the motorcycle to delete.
        :return: None
        """
        self.repository.delete_motorcycle_by_vin(vin=vin)


def provide_motorcycle_service(db_session: Session) -> MotorcycleService:
    """
    Dependency provider for MotorcycleService.

    :param db_session: Session - The SQLAlchemy session to use for the service.
    :return: MotorcycleService - An instance of MotorcycleService.
    """
    return MotorcycleService(session=db_session)


class MotorcycleController(Controller):
    """
    Controller for Motorcycle operations.
    """
    path = "/motorcycles"
    dependencies = {"motorcycle_service": Provide(provide_motorcycle_service, sync_to_thread=False)}

    @get("/", response_model=List[MotorcycleResponse])
    def list_motorcycles(self, motorcycle_service: MotorcycleService) -> List[MotorcycleResponse]:
        """
        List all motorcycles entries.

        :param motorcycle_service: MotorcycleService - The service to handle database operations.
        :return: List[MotorcycleResponse] - A list of MotorcycleResponse instances.
        """
        return motorcycle_service.list_motorcycles()

    @get("/{vin:str}", response_model=MotorcycleResponse)
    def get_motorcycle_by_vin(self, motorcycle_service: MotorcycleService, vin: str) -> MotorcycleResponse:
        """
        Get a specific motorcycle by its VIN.

        :param motorcycle_service: MotorcycleService - The service to handle database operations.
        :param vin: str - The VIN of the motorcycle to retrieve.
        :return: MotorcycleResponse - The motorcycle instance with the specified VIN.
        """
        return motorcycle_service.get_motorcycle_by_vin(vin=vin)

    @post("/", response_model=MotorcycleResponse)
    def create_motorcycle(self, motorcycle_service: MotorcycleService, data: MotorcycleCreate) -> MotorcycleResponse:
        """
        Create a new motorcycle entry.

        :param motorcycle_service: MotorcycleService - The service to handle database operations.
        :param data: MotorcycleCreate - The new Motorcycle entry data.
        :return: MotorcycleResponse - The created Motorcycle instance.
        """
        return motorcycle_service.create_motorcycle(data=data)

    @put("/{vin:str}", response_model=MotorcycleResponse)
    def update_motorcycle(
            self, motorcycle_service: MotorcycleService, vin: str, data: MotorcycleUpdate
    ) -> MotorcycleResponse:
        """
        Update an existing motorcycle entry.

        :param motorcycle_service: MotorcycleService - The service to handle database operations.
        :param vin: str - The VIN of the motorcycle to update.
        :param data: MotorcycleUpdate - The data to update with.
        :return: MotorcycleResponse - The updated Motorcycle instance.
        """
        return motorcycle_service.update_motorcycle(vin=vin, data=data)

    @patch("/{vin:str}", response_model=MotorcycleResponse)
    def partially_update_motorcycle(
        self, motorcycle_service: MotorcycleService, vin: str, data: MotorcycleUpdate
    ) -> MotorcycleResponse:
        """
        Partially update an existing motorcycle entry.

        :param motorcycle_service: MotorcycleService - The service to handle database operations.
        :param vin: str - The VIN of the motorcycle to update.
        :param data: MotorcycleUpdate - The data to update with, allowing optional fields.
        :return: MotorcycleResponse - The updated Motorcycle instance.
        """
        return motorcycle_service.update_motorcycle(vin=vin, data=data)

    @delete("/{vin:str}")
    def delete_motorcycle_by_vin(self, motorcycle_service: MotorcycleService, vin: str) -> None:
        motorcycle_service.delete_motorcycle_by_vin(vin=vin)


SQLALCHEMY_DATABASE_URL = "postgresql://motorycle_db:password@localhost:5432/dev_motorycle_db"
sqlalchemy_config = SQLAlchemySyncConfig(connection_string=SQLALCHEMY_DATABASE_URL)
sqlalchemy_plugin = SQLAlchemyInitPlugin(config=sqlalchemy_config)


def on_startup() -> None:
    """
    Function to run on application startup.
    """
    with sqlalchemy_config.get_engine().begin() as connection:
        base.BigIntBase.metadata.create_all(connection)


app = Litestar(
    route_handlers=[MotorcycleController],
    on_startup=[on_startup],
    plugins=[SQLAlchemyInitPlugin(config=sqlalchemy_config)],
    path="/api"
)
