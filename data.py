from utilities import connect, retrieve, store

class Lore():

    def __repr__(self):
        return f"<Lore object, Level: {self.level}, Key: {self.key}, Value: {str(self.value)}>"

    

    def __bool__(self):
        return bool(self.data)


    def __str__(self):
        return str(self.value)


    def __init__(self, key, level):
        self.key = key
        self.level = level

        data = self.retrieve_data()
        self.data = data

        if self.data:
            self.data_type = data.get('data_type')
            self.value = data.get('value')

            self.datetime = data.get('datetime')
            self.label = data.get('label')
            self.bool = True
        else:
            self.data_type, self.value, self.datetime, self.label = None, None, None, None
            self.bool = False


    def register(self):
        if self.data_type == 'register':
            return True
        else:
            return False


    def retrieve_data(self):

        return retrieve(self.key, register=self.level, fetch='last')

    def store(self):
        """Store the current state of the object."""
        return store(self.key, self.value, label=self.label, data_type=self.data_type, register=self.level)

lorem = Lore('f', 1)



