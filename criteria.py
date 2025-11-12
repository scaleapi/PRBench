import pdb

FIELD_MAP = {"Legal": "law", "Finance": "finance"}

class Criterion:
    def __init__(self, d):
        self.d = d['annotations']
        self.d['id'] = d['id']
        self.d['title'] = d['title']
        self.find_weight()
        self.find_criteria_category()

    def find_weight(self):
        self.d["weight"] = self.d[self.d['weight_class'].replace(" ", "_")+"_weight"]

    def find_criteria_category(self):
        self.d['criteria_category'] = None
        for k, v in self.d.items():
            if "criteria_category" in k:
                self.d['criteria_category'] = v

    def get_weight(self):
        return self.d['weight']

    def get_title(self):
        return self.d['title']

    def get_id(self):
        return self.d['id']

    def get_category(self):
        return self.d['criteria_category']

    def get_field_for_category(self):
        if "field_for_category" in self.d:
            return self.d["field_for_category"]
        return None

    def __repr__(self):
        ss = "Criterion:"
        ss += f"\nTitle: {self.d['title']}"
        ss += f"\nWeight: {self.d['weight']}"
        ss += f"\nCategory: {self.d['criteria_category']}"
        if "field_for_category" in self.d:
            ss += f"\nField for category: {self.d['field_for_category']}\n"
        return ss