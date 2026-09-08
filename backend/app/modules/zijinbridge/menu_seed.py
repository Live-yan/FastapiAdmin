from sqlalchemy import select

from app.core.database import async_db_session
from app.core.logger import logger
from app.modules.system.menu.model import MenuModel
from app.modules.system.role.model import RoleMenusModel, RoleModel


ROOT_ROUTE_NAME = "IndustrialData"
CONSOLE_ROUTE_NAME = "ZijinBridgeConsole"


async def ensure_zijinbridge_menu() -> None:
    """幂等补齐紫金桥菜单与 ADMIN/SUPER_ADMIN 权限。

    FastapiAdmin 的基础种子只会在 sys_menu 为空时整体导入；已有项目升级时，
    因此需要显式补齐本模块菜单，避免用户合并代码后页面不可见。
    """

    async with async_db_session() as session, session.begin():
        root = (
            await session.execute(select(MenuModel).where(MenuModel.route_name == ROOT_ROUTE_NAME))
        ).scalars().first()
        if root is None:
            root = MenuModel(
                name="工业数据",
                type=1,
                icon="ri:database-2-line",
                order=4,
                route_name=ROOT_ROUTE_NAME,
                route_path="/industrial",
                redirect="/industrial/zijinbridge",
                title="工业数据",
                always_show=True,
                description="工业实时数据库与数据服务管理",
            )
            session.add(root)
            await session.flush()

        console = (
            await session.execute(select(MenuModel).where(MenuModel.route_name == CONSOLE_ROUTE_NAME))
        ).scalars().first()
        if console is None:
            console = MenuModel(
                name="紫金桥管理",
                type=2,
                icon="ri:pulse-line",
                order=1,
                permission="module_zijinbridge:query",
                route_name=CONSOLE_ROUTE_NAME,
                route_path="zijinbridge",
                component_path="module_zijinbridge/index",
                title="紫金桥管理",
                description="实时数据、历史数据、报警、SQL 与批量导出",
                parent_id=root.id,
            )
            session.add(console)
            await session.flush()
        elif console.parent_id != root.id:
            console.parent_id = root.id

        button_specs = [
            ("查询", "module_zijinbridge:query", 1),
            ("数据写入", "module_zijinbridge:write", 2),
            ("SQL 控制台", "module_zijinbridge:sql", 3),
        ]
        managed_menus: list[MenuModel] = [root, console]
        for name, permission, order in button_specs:
            button = (
                await session.execute(
                    select(MenuModel).where(
                        MenuModel.parent_id == console.id,
                        MenuModel.type == 3,
                        MenuModel.permission == permission,
                    )
                )
            ).scalars().first()
            if button is None:
                button = MenuModel(
                    name=name,
                    type=3,
                    order=order,
                    permission=permission,
                    title=name,
                    parent_id=console.id,
                    description="紫金桥管理工具权限",
                )
                session.add(button)
                await session.flush()
            managed_menus.append(button)

        roles = (
            await session.execute(
                select(RoleModel).where(RoleModel.code.in_(["SUPER_ADMIN", "ADMIN"]))
            )
        ).scalars().all()
        added = 0
        for role in roles:
            for menu in managed_menus:
                if await session.get(
                    RoleMenusModel,
                    {"role_id": role.id, "menu_id": menu.id},
                ) is None:
                    session.add(RoleMenusModel(role_id=role.id, menu_id=menu.id))
                    added += 1

        logger.info(
            "✅ 紫金桥管理菜单已就绪（菜单 {} 项，新增角色授权 {} 项；已有在线用户需重新登录以刷新权限）",
            len(managed_menus),
            added,
        )
