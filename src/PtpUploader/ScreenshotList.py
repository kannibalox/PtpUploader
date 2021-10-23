import json


# For sake of simple JSON serialization an item is a simple list.
# Item[ 0 ] = name
# Item[ 1 ] = list of screenshots
class ScreenshotList:
    def __init__(self):
        self.Items = []

    def GetAsString(self):
        return json.dumps(self.Items)

    def LoadFromString(self, screenshotListString):
        try:
            self.Items = json.loads(screenshotListString)
        except Exception:
            self.Items = []

    def __GetItemByName(self, name):
        for item in self.Items:
            if item[0] == name:
                return item

        return None

    def GetScreenshotsByName(self, name):
        item = self.__GetItemByName(name)
        if item is None:
            return None
        else:
            return item[1]

    def SetScreenshots(self, name, screenshots):
        item = self.__GetItemByName(name)
        if item is None:
            item = [name, screenshots]
            self.Items.append(item)
        else:
            item[1] = screenshots
