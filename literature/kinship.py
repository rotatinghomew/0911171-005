"""已登记亲属组：组内成员与长幼位置。"""

from copy import deepcopy


class KinshipRegistry:
    def __init__(self) -> None:
        self.groups: dict[str, dict] = {}

    def register(self, group_id: str, members: list[dict], work: str | None = None, label: str | None = None) -> dict:
        if group_id in self.groups:
            raise ValueError(f"亲属组已登记: {group_id}")
        if not members:
            raise ValueError("亲属组不能为空")
        characters = [m["character"] for m in members]
        if len(set(characters)) != len(characters):
            raise ValueError("亲属组内人物重复")
        orders = sorted(m["birth_order"] for m in members)
        if orders != list(range(1, len(members) + 1)):
            raise ValueError("长幼位置必须从 1 开始连续编号")
        group = {
            "group": group_id,
            "work": work,
            "label": label,
            "members": deepcopy(members),
        }
        self.groups[group_id] = group
        return deepcopy(group)

    def get(self, group_id: str) -> dict:
        if group_id not in self.groups:
            raise ValueError(f"未登记的亲属组: {group_id}")
        return deepcopy(self.groups[group_id])

    def position_of(self, group_id: str, character: str) -> int:
        for member in self.get(group_id)["members"]:
            if member["character"] == character:
                return member["birth_order"]
        raise ValueError(f"人物不在亲属组 {group_id} 内: {character}")
