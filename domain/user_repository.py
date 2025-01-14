from abc import abstractmethod, ABC
from typing import List

from domain.user import User


class IUserRepository(ABC): # Interface
    @abstractmethod
    async def add(self, user: User):
        pass

    async def update(self, user: User):
        pass

    @abstractmethod
    async def get(self, telegram_user_id: int, telegram_chat_id: int) -> User | None:
        pass

    @abstractmethod
    async def get_all_by_user_id(self, telegram_chat_id: int) -> List[User] | None:
        pass

    @abstractmethod
    async def get_all_by_chat_id(self, telegram_chat_id: int) -> List[User] | None:
        pass

    @abstractmethod
    async def update(self, user: User):
        pass