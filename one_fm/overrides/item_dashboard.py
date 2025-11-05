def get_data(**kwargs):
    data = kwargs.get('data')

    if data and 'transactions' in data:
        # Find the group with a stable property, e.g., label == "Buy"
        buy_group_index = None
        for idx, group in enumerate(data['transactions']):
            if group.get('label') == "Buy":
                buy_group_index = idx
                break
        if buy_group_index is not None:
            buy_group_details = data['transactions'][buy_group_index]
            buy_items = buy_group_details.get('items', [])
            buy_items = buy_items[:1] + ["Request for Material", "Request for Purchase"] + buy_items[1:]
            buy_group = {
                **buy_group_details,
                "items": buy_items
            }
            data['transactions'][buy_group_index] = buy_group

    return data