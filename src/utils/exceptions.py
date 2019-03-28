class JalBotError(Exception):
    """base class for JalBot errors"""
    pass


class JalBotExampleError(JalBotError):
    """base class for JalBot Example errors"""
    pass

class NHLException(JalBotError):
    """Base class for NHL exceptions"""
    pass


class NBAException(Exception):
    """Base class for NBA exceptions"""
    pass


class NBATeamError(Exception):
    """Base class for NBATeam Errors"""
    pass


class MLBException(Exception):
    """Base class for MLB exceptions"""
    pass


class NHLTeamError(Exception):
    """Base class for NHLTeam Errors"""
    pass

class NHLTeamException(Exception):
    """Base class for NHLTeam Errors"""
    pass


class NHLPlayerError(Exception):
    """Base class for NHLTeam Errors"""
    pass

class NHLPlayerException(Exception):
    """Base clas for NHLPlayer errors"""
    pass

class NHLRequestException(NHLException):
    """Base class for NHL request exceptions"""
    pass

class NFLRequestException(Exception):
    """Base class for NFL API requests exceptions"""
    pass
