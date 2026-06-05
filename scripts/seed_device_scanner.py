"""Seed device scanner catalog: issues, brands, chipsets, tools, capabilities, compatibility."""

import uuid
from decimal import Decimal
from sqlmodel import Session, select, and_
from app.database import get_session
from app.models.device_catalog import (
    IssueCategory,
    Chipset,
    DeviceBrand,
    Tool,
    ToolCapability,
    DeviceCompatibility,
)
from app.models.item import Item


ISSUES = [
    ("frp", "FRP Lock"),
    ("network_lock", "Network Lock"),
    ("mdm", "MDM Lock"),
    ("icloud", "iCloud Lock"),
    ("password", "Password / Pattern Lock"),
    ("corrupt_os", "Corrupt OS"),
]

CHIPSETS = [
    ("mediatek", "MediaTek"),
    ("snapdragon", "Qualcomm Snapdragon"),
    ("exynos", "Samsung Exynos"),
    ("tensor", "Google Tensor"),
    ("unisoc", "Unisoc"),
    ("apple", "Apple"),
]

BRANDS = [
    ("samsung", "Samsung"),
    ("apple", "Apple"),
    ("google", "Google"),
    ("xiaomi", "Xiaomi"),
    ("realme", "Realme"),
    ("tecno", "Tecno"),
    ("generic", "Generic / Other"),
]

TOOLS = [
    {
        "slug": "unlock-tool",
        "name": "Unlock Tool",
        "description": "Repair tool for FRP, pattern, and various account unlocks.",
        "website_url": "https://unlocktool.net",
        "issues": ["frp", "password"],
        "brands": ["samsung", "generic"],
        "chipsets": ["exynos", "snapdragon", "mediatek", "unisoc"],
    },
    {
        "slug": "dft-pro",
        "name": "DFT Pro",
        "description": "Mobile diagnostics and flashing utility.",
        "website_url": "https://dftpro.com",
        "issues": ["frp", "network_lock", "corrupt_os", "password"],
        "brands": ["samsung", "generic"],
        "chipsets": ["exynos", "snapdragon"],
    },
    {
        "slug": "octoplus",
        "name": "Octoplus",
        "description": "Dongle-based tool for Samsung, Huawei, and other brands.",
        "website_url": "https://octoplus.com",
        "issues": ["frp", "network_lock", "mdm", "password", "corrupt_os"],
        "brands": ["samsung", "generic"],
        "chipsets": ["exynos", "snapdragon"],
    },
    {
        "slug": "hydra-tool",
        "name": "Hydra Tool",
        "description": "License/dongle-free mobile unlocking solution.",
        "website_url": "https://hydratool.com",
        "issues": ["frp", "network_lock", "password", "icloud"],
        "brands": ["samsung", "generic", "apple"],
        "chipsets": ["exynos", "snapdragon", "apple"],
    },
    {
        "slug": "kg-killer",
        "name": "KG Killer",
        "description": "Specialized Samsung KG lock removal utility.",
        "website_url": "https://kgkiller.com",
        "issues": ["frp", "network_lock", "password"],
        "brands": ["samsung"],
        "chipsets": ["exynos", "snapdragon"],
    },
    {
        "slug": "mtk-bypass",
        "name": "MTK Bypass Tool",
        "description": "MediaTek-focused FRP and auth bypass utility.",
        "website_url": "https://example.com/mtk-bypass",
        "issues": ["frp", "password", "mdm"],
        "brands": ["generic", "xiaomi", "tecno", "realme"],
        "chipsets": ["mediatek", "unisoc"],
    },
    {
        "slug": "samfirm",
        "name": "SamFirm / FRP Tool",
        "description": "Samsung firmware and FRP removal helper.",
        "website_url": "https://example.com/samfirm",
        "issues": ["frp", "corrupt_os", "password"],
        "brands": ["samsung"],
        "chipsets": ["exynos", "snapdragon"],
    },
    {
        "slug": "iremove",
        "name": "iRemoval Pro",
        "description": "Apple iCloud/FMI and activation bypass utilities.",
        "website_url": "https://iremove.tools",
        "issues": ["icloud", "password"],
        "brands": ["apple"],
        "chipsets": ["apple"],
    },
    {
        "slug": "checkra1n",
        "name": "Checkra1n",
        "description": "Boot-level exploit-based tool for older iOS devices.",
        "website_url": "https://checkra.in",
        "issues": ["icloud", "password", "mdm"],
        "brands": ["apple"],
        "chipsets": ["apple"],
    },
    {
        "slug": "mtkclient",
        "name": "MTK Client",
        "description": "Open-source MediaTek device communication and flash tool.",
        "website_url": "https://github.com/bkerler/mtkclient",
        "issues": ["frp", "mdm", "corrupt_os", "password"],
        "brands": ["generic", "xiaomi", "tecno"],
        "chipsets": ["mediatek"],
    },
]

COMPATIBILITIES_EXTRA = [
    # brand, chipset, tool_slugs
    ("google", "tensor", ["unlock-tool", "hydra-tool"]),
    ("xiaomi", "mediatek", ["mtk-bypass", "mtkclient"]),
    ("xiaomi", "snapdragon", ["unlock-tool", "hydra-tool"]),
    ("realme", "mediatek", ["mtk-bypass", "mtkclient"]),
    ("tecno", "mediatek", ["mtk-bypass", "mtkclient"]),
    ("tecno", "unisoc", ["mtk-bypass", "mtkclient"]),
    ("samsung", "exynos", ["kg-killer", "samfirm"]),
]


def get_or_create(session, model, lookup, defaults):
    instance = session.exec(lookup).first()
    if instance:
        for k, v in defaults.items():
            if getattr(instance, k) != v:
                setattr(instance, k, v)
        session.add(instance)
        return instance

    new_instance = model(**defaults)
    session.add(new_instance)
    session.flush()
    return new_instance


def seed_devices():
    with next(get_session()) as session:
        for slug, label in ISSUES:
            get_or_create(
                session,
                IssueCategory,
                select(IssueCategory).where(IssueCategory.slug == slug),
                {"slug": slug, "label": label, "is_active": True},
            )

        for key, label in CHIPSETS:
            get_or_create(
                session,
                Chipset,
                select(Chipset).where(Chipset.key == key),
                {"key": key, "label": label},
            )

        for slug, name in BRANDS:
            get_or_create(
                session,
                DeviceBrand,
                select(DeviceBrand).where(DeviceBrand.slug == slug),
                {"slug": slug, "name": name, "is_active": True},
            )

        tool_lookup = {}
        for t in TOOLS:
            tool_obj = get_or_create(
                session,
                Tool,
                select(Tool).where(Tool.slug == t["slug"]),
                {
                    "slug": t["slug"],
                    "name": t["name"],
                    "description": t.get("description"),
                    "website_url": t.get("website_url"),
                    "is_active": True,
                },
            )
            tool_lookup[t["slug"]] = tool_obj

            for issue_slug in t.get("issues", []):
                existing_cap = session.exec(
                    select(ToolCapability).where(
                        and_(
                            ToolCapability.tool_id == tool_obj.id,
                            ToolCapability.issue_slug == issue_slug,
                        )
                    )
                ).first()
                if not existing_cap:
                    cap = ToolCapability(
                        tool_id=tool_obj.id,
                        issue_slug=issue_slug,
                        is_active=True,
                    )
                    session.add(cap)

        session.commit()

        for brand_slug, chipset_key, tool_slugs in COMPATIBILITIES_EXTRA:
            for tool_slug in tool_slugs:
                tool = tool_lookup.get(tool_slug)
                if not tool:
                    continue
                existing_comp = session.exec(
                    select(DeviceCompatibility).where(
                        and_(
                            DeviceCompatibility.tool_id == tool.id,
                            DeviceCompatibility.brand_slug == brand_slug,
                            DeviceCompatibility.chipset_key == chipset_key,
                        )
                    )
                ).first()
                if not existing_comp:
                    comp = DeviceCompatibility(
                        tool_id=tool.id,
                        brand_slug=brand_slug,
                        chipset_key=chipset_key,
                        is_active=True,
                    )
                    session.add(comp)

        session.commit()

        for tool in session.exec(select(Tool).where(Tool.is_active == True)).all():
            tool_item = session.exec(
                select(Item).where(Item.slug == tool.slug, Item.is_archived == False)
            ).first()
            if not tool_item:
                tool_item = Item(
                    uid=str(uuid.uuid4()),
                    slug=tool.slug,
                    title=tool.name,
                    description=tool.description or "Device scanner recommended tool.",
                    item_type="SERVICE",
                    category="tool_rental",
                    price_markup=Decimal("0.00"),
                    currency="USD",
                )
                session.add(tool_item)
                session.commit()
                session.refresh(tool_item)
                print(f"Created Item for tool: {tool.slug}")
            else:
                print(f"Item exists for tool: {tool.slug}")

        print("Done: device scanner catalog seeded.")


if __name__ == "__main__":
    seed_devices()
