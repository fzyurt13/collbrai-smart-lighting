from config.profiles import PROFILES


class ProfileManager:
    def __init__(self):
        self.profiles = PROFILES

    def list_profiles(self):
        return list(self.profiles.keys())

    def exists(self, profile_name):
        return profile_name in self.profiles

    def get(self, profile_name):
        if profile_name not in self.profiles:
            raise ValueError(
                "Unknown lighting profile: {}".format(profile_name)
            )

        return self.profiles[profile_name]
