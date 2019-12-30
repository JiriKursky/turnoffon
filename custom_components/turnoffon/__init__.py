"""
Component for controlling devices in regular time

Tested on under hass.io ver. 0.93.2 

Version 20.6.2019

"""

import logging
import datetime
import time
import os
import sys

import voluptuous as vol

from homeassistant.const import (ATTR_ENTITY_ID, CONF_ICON, CONF_NAME, SERVICE_TURN_ON, SERVICE_TURN_OFF, STATE_ON, STATE_OFF, EVENT_HOMEASSISTANT_STOP,
CONF_COMMAND_ON, CONF_COMMAND_OFF, CONF_CONDITION, WEEKDAYS)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util
from homeassistant.core import split_entity_id
from homeassistant.helpers.event import async_call_later
from homeassistant.components.input_datetime import InputDatetime, ATTR_DATE, ATTR_TIME, SERVICE_SET_DATETIME

DOMAIN = 'turnoffon'
ENTITY_ID_FORMAT = DOMAIN + '.{}'

from inspect import currentframe, getframeinfo
_LOGGER = logging.getLogger(__name__)

LI_NO_DEFINITION = 'No entity added'

CONF_WEEKDAYS               = 'weekdays'
CONF_ACTION_ENTITY_ID       = 'action_entity_id'        # what to call as controlling entity during comand_on, comannd_off
CONF_FORCE_INITIAL          = 'force_initial'           # true -> it will after each restart use initial_values
CONF_FORCE_TURN             = 'force_turn'              # true -> if switch is changed not via HA - it will turn to state according HA
CONF_INPUT_DATETIME         = 'input_datetime'          # true  -> will be created input_datetime entities
CONF_LINKED_ENTITY_ID       = 'linked_entity_id'        # linked entity_id will be on and off acording CONF_ACTION_ENTITY_ID
CONF_TIMERS                 = 'timers'

SCAN_INTERVAL = 59
SHUT_DOWN = False                               # shutting down on stop HA

O_PARENT = 'PARENT'
O_CHILDREN = 'CHILDREN'

# Used attributes
ATTR_WEEKDAYS           = 'weekdays'
ATTR_START_TIME         = 'start_time'
ATTR_TIME_DELTA         = 'time_delta'
ATTR_END_TIME           = 'end_time'
ATTR_LAST_RUN               = 'last_run'
ATTR_START_TIME_INIT        = 'start_time_init'
ATTR_END_TIME_INIT          = 'end_time_init'
ATTR_LINKED_ENTITY_ID       = 'linked_entity_id'


ATTR_ACTIVE_CHILD_ID   = 'active_child_id'
# There are several entities defined by this routine, but only one have to be active in interval


def my_debug(s):
    cf = currentframe()
    line = cf.f_back.f_lineno
    if s is None:
            s = ''
    _LOGGER.debug("line: {} -> {}".format(line, s))

def time_to_string(t_cas):
    try :
        return t_cas.strftime('%H:%M')
    except :
        return None

def string_to_time(s):
    try:
        ret_val = time.strptime(s, '%H:%M')         
    except:
        my_debug("Was not possible to convert string to time: {}".format(s))
        ret_val = None
    return ret_val

def prevedCasPar(sCas, just_now):    
    try:
        def_time = string_to_time(sCas)
        if def_time is None:
            ret_val =  None
        else:
            just_now = datetime.datetime.now()    
            ret_val = just_now.replace(hour=def_time.tm_hour, minute=def_time.tm_min, second=0)
    except:
        my_debug("Was not possible to convert time: {}".format(sCas))
        ret_val = None
    return ret_val

def prevedCas(sCas):
    # String to datetime now
    return prevedCasPar(sCas, datetime.datetime.now())

def get_end_time_delta(start_time, delta):
    try:
        ret_val = time_to_string(prevedCas(start_time) + datetime.timedelta(minutes = delta))
    except: 
        my_debug("{} delta: {}".format(start_time, delta))
        ret_val = None
    return ret_val

def get_end_time(start_time, end_time) :    
    if isinstance(end_time, int):        
        return get_end_time_delta(start_time, end_time)
    return end_time


# Service for running timer immediately
SERVICE_RUN_CASOVAC = 'run_turnoffon'
SERVICE_SET_RUN_CASOVAC_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id
})


# Service setting time run-time
def has_start_or_end(conf):
    """Check at least date or time is true."""
    if conf[ATTR_TIME_DELTA] and not conf[ATTR_START_TIME]:
        raise vol.Invalid("In case of delta {} is required".format(ATTR_START_TIME))                            
    if conf[ATTR_START_TIME] or conf[ATTR_END_TIME]:
         return conf    
    raise vol.Invalid("Entity needs at least a {} and {} or {}".format(ATTR_START_TIME, ATTR_END_TIME, ATTR_TIME_DELTA))

SERVICE_SET_TIME = 'set_time'
SERVICE_SET_TIME_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id,    
    vol.Optional(ATTR_START_TIME): cv.time,
    vol.Optional(ATTR_END_TIME): cv.time,            
    vol.Optional(ATTR_TIME_DELTA): vol.All(vol.Coerce(int), vol.Range(min=1, max=59), msg='Invalid '+ATTR_TIME_DELTA)},
    has_start_or_end
)

# Konstanta definice sluzby
SERVICE_SET_TURN_ON = SERVICE_TURN_ON
SERVICE_SET_TURN_ON_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id    
})

# Konstanta definice sluzby
SERVICE_SET_TURN_OFF = SERVICE_TURN_OFF
SERVICE_SET_TURN_OFF_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id    
})

SERVICE_RESET_TIMERS = 'reset_timers'
SERVICE_RESET_TIMERS_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id    
})


ERR_CONFIG_TIME_SCHEMA = 'Wrong timers'
ERR_CONFIG_TIME_2 = 'Time delta must be in range 1 - 59'
ERR_CONFIG_WEEKDAY = 'Wrong week day: {}'
ERR_CONFIG_WEEKDAYS = 'Wrong definition of weekdays'

# End services

def kontrolaCasy(hodnota):
    """ Checking timers during config """   
    try:    
        for start, cosi in hodnota.items():        
            cv.time(start)        
            if  isinstance(cosi, int):                
                if (cosi<0) or (cosi > 59):
                    raise vol.Invalid(ERR_CONFIG_TIME_2)    
            else:                
                cv.time(cosi)            
        return hodnota
    except:
        raise vol.Invalid(ERR_CONFIG_TIME_SCHEMA)    

def check_weekdays(value):
    try:    
        for inv in value:        
            if not inv in WEEKDAYS:
                raise vol.Invalid(ERR_CONFIG_WEEKDAY.format(inv))                
        return value
    except:
        raise vol.Invalid(ERR_CONFIG_WEEKDAYS)        

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: cv.schema_with_slug_keys(
        vol.All({                        
            vol.Required(CONF_TIMERS): kontrolaCasy,
            vol.Optional(CONF_WEEKDAYS): check_weekdays,
            vol.Required(CONF_ACTION_ENTITY_ID): cv.entity_id,            
            vol.Optional(CONF_LINKED_ENTITY_ID): cv.entity_id,            
            vol.Optional(CONF_CONDITION): cv.entity_id,
            vol.Optional(CONF_NAME): cv.string,
            vol.Optional(CONF_COMMAND_ON, default = SERVICE_TURN_ON): cv.string,
            vol.Optional(CONF_COMMAND_OFF, default = SERVICE_TURN_OFF): cv.string,
            vol.Optional(CONF_FORCE_TURN, default = True): cv.boolean,
            vol.Optional(CONF_FORCE_INITIAL, default = True): cv.boolean,
            vol.Optional(CONF_INPUT_DATETIME, default = False): cv.boolean,
        })
    )
}, extra=vol.ALLOW_EXTRA)

def get_child_object_id(parent, number):
    """ Returning child object entity_id """
    if number < 10:
        s_number = "0" + str(number) 
    else:
        s_number = str(number) 
    return "{}_{}".format(parent, s_number)

async def async_setup(hass, config):
    """First setup."""
    component = EntityComponent(_LOGGER, DOMAIN, hass)
    component_input_datetime = EntityComponent(_LOGGER, "input_datetime", hass)
    entities = []
    entities_input_datetime = []

    # Store entities. I think it is sick, should use call service instead, but loops and loops
    hass.data[DOMAIN] = { O_PARENT: {}, O_CHILDREN: {}}
    

    # Reading in config
    for object_id, cfg in config[DOMAIN].items():    
        if cfg is None:            
            return False        
        casy = cfg.get(CONF_TIMERS)
        if casy is None:
            _LOGGER.info(LI_NO_DEFINITION)
            return False
        
        # Default creation of name or from config        
        parent_name = cfg.get(CONF_NAME) 
        if parent_name is None:
            parent_name = object_id
        input_datetime = cfg.get(CONF_INPUT_DATETIME)
        # citac
        i = 0    
        for start_time, end_time in casy.items():
            i += 1            
            new_object_id = get_child_object_id(object_id, i)
            name = "{} {}".format(parent_name, i)
            
            # definition of children
            end_time = get_end_time(start_time, end_time)   # konecny cas                
            casovac = Casovac(hass, new_object_id, name, start_time, end_time, cfg.get(CONF_WEEKDAYS), cfg.get(CONF_FORCE_INITIAL))
            my_debug("entity: {} setting up: {}".format(casovac, new_object_id))              
            hass.data[DOMAIN][O_CHILDREN][new_object_id] = casovac                                    
            
            if input_datetime :
                input_object_id = "s_{}".format(new_object_id)
                name_input = "{} start".format(name)
                edit_start = M_InputDatetime(input_object_id, name_input, start_time, new_object_id, True)
                #edit_start = M_InputDatetime(input_object_id, name_input, False, True, None, start_time)
                entities_input_datetime.append(edit_start)

                name_input = "{} end".format(name)
                input_object_id = "e_{}".format(new_object_id)
                edit_end = M_InputDatetime(input_object_id, name_input, end_time, new_object_id, False)
                #edit_end = InputDatetime(input_object_id, name_input, False, True, None, end_time)
                entities_input_datetime.append(edit_end)
                casovac.edit_entity(edit_start, edit_end)
            entities.append(casovac)
            
        # Create entity_id
        casovacHlavni = CasovacHlavni(hass, object_id, parent_name, i, cfg)

        # Push to store
        hass.data[DOMAIN][O_PARENT][object_id] = casovacHlavni        

        # Setting main timer - loop for checking interval        
        """
        async_track_time_interval(hass, casovacHlavni.regular_loop(),
                        datetime.timedelta(seconds=SCAN_INTERVAL))
        """
        async_call_later(hass, SCAN_INTERVAL, casovacHlavni.regular_loop())
        entities.append(casovacHlavni)        
    if not entities:
        _LOGGER.info(LI_NO_DEFINITION)    
        return False
    

    # Musi byt pridano az po definici vyse - je potreba znat pocet zaregistrovanych casovacu    
    async def async_run_casovac_service(entity, call):
        """Main procedure. Called from parent entity """                
        # entity is parent entity
        #----------------------------
        # main procedure
        my_debug("calling get us what to do")
        await entity.run_casovac()
        #----------------------------
        
        # what will be controlled
        hass = entity.hass
        try:        
            action_entity = hass.states.get(entity.action_entity_id)
            target_domain, _ = split_entity_id(action_entity.entity_id)
            to_do = entity.to_do
        except:
            _LOGGER.error("Wrong entity {}".format(entity.action_entity_id))
            return
        

        # turn off or turn on? decide here
        changed_state = ((entity._set_on(to_do) and not is_on(action_entity)) or (not entity._set_on(to_do) and is_on(action_entity)))       
        call_service =  changed_state or entity.force_turn
        my_debug(" what: {} set_on: {} is_on: {} {} {}".format(call_service, entity._set_on(to_do), is_on(action_entity), entity.force_turn, entity.entity_id))
        
        if entity.linked_entity_id is not None and changed_state:
            domain, _ = split_entity_id(entity.linked_entity_id)
            my_debug("linked entity:{} {} {}".format(target_domain, to_do, entity.linked_entity_id))
            await hass.services.async_call(domain, to_do, { ATTR_ENTITY_ID: entity.linked_entity_id }, blocking=True)

        if call_service:
            my_debug("calling service {} {} {}".format(target_domain, to_do, action_entity.entity_id))                                
            # Calling entity to switch off or on
            await hass.services.async_call(target_domain, to_do, { ATTR_ENTITY_ID: action_entity.entity_id }, blocking=True)
        else:
            my_debug("entity {} in right state, {} not necessary".format(action_entity.entity_id, to_do))

    # Service registering         
    component.async_register_entity_service(
        SERVICE_RUN_CASOVAC, SERVICE_SET_RUN_CASOVAC_SCHEMA, 
        async_run_casovac_service
    )

    async def async_set_time_service(entity, call):
        """Spusteni behu."""
        try: 
            start_time = call.data.get(ATTR_START_TIME)
            end_time = call.data.get(ATTR_END_TIME)   
            if end_time is None:                     
                delta = call.data.get(ATTR_TIME_DELTA)
                if delta is not None:                    
                    just_now = datetime.datetime.now()                        
                    start = just_now.replace(hour=start_time.hour, minute=start_time.minute, second=0)                    
                    end_time =start + datetime.timedelta(minutes = delta)                    
            entity.set_time(start_time, end_time)        
        except:
            raise ValueError('Wrong time parametres')        
    component.async_register_entity_service(
        SERVICE_SET_TIME, SERVICE_SET_TIME_SCHEMA, 
        async_set_time_service
    )
    
    async def async_set_turn_on_service(entity, call):        
        """Calling entity to turn_on."""        
        entity.set_turn_on()        

    component.async_register_entity_service(
        SERVICE_SET_TURN_ON, SERVICE_SET_TURN_ON_SCHEMA, 
        async_set_turn_on_service
    )

    async def async_set_turn_off_service(entity, call):
        """Setting turn_off."""        
        entity.set_turn_off()        
    component.async_register_entity_service(
        SERVICE_SET_TURN_OFF, SERVICE_SET_TURN_OFF_SCHEMA, 
        async_set_turn_off_service
    )

    async def async_reset_timers(entity, call): 
        await entity.reset_timers()

    component.async_register_entity_service(
        SERVICE_RESET_TIMERS, SERVICE_RESET_TIMERS_SCHEMA, 
        async_reset_timers
    )


    async def async_set_datetime_service(entity, call):
        """Handle a call to the input datetime 'set datetime' service."""
        time = call.data.get(ATTR_TIME)
        date = call.data.get(ATTR_DATE)
        if (entity.has_date and not date) or (entity.has_time and not time):
            _LOGGER.error("Invalid service data for %s "
                          "input_datetime.set_datetime: %s",
                          entity.entity_id, str(call.data))
            return

        entity.async_set_datetime(date, time)

    if entities_input_datetime :
        component_input_datetime.async_register_entity_service(
            SERVICE_SET_DATETIME, async_set_datetime_service
        )

    # Adding all entities
    await component.async_add_entities(entities)
    if entities_input_datetime :
        await component_input_datetime.async_add_entities(entities_input_datetime)

    # Stopping with Homeassistant
    async def stop_turnoffon(event):
        """Disconnect."""
        my_debug("Shutting down")
        SHUT_DOWN = True                
        
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_turnoffon)    
    

    return True

def is_on(entity):
    return entity.state == STATE_ON

class TurnonoffEntity(RestoreEntity):
    """ Prototype entity for both. Parent and children """
    def __init__(self, hass, object_id, parent, name):
        self.entity_id = ENTITY_ID_FORMAT.format(object_id) # definice identifikatoru        
        self._name = name
        self._parent = parent
        self._last_run = None        

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return 'mdi:timer'
        
    def set_turn_on(self):
        raise ValueError('For children entity not allowed')

    def set_turn_off(self):
        raise ValueError('For children entity not allowed')

    def set_last_run(self):
        """ Update attributu ATTR_LAST_RUN """
        self._last_run = datetime.datetime.now() 
        self.async_schedule_update_ha_state()
    
    async def async_added_to_hass(self):        
        """Run when entity about to be added."""
        await super().async_added_to_hass()        
        old_state = await self.async_get_last_state()
        if old_state is not None:                            
            self._last_run =  old_state.attributes.get(ATTR_LAST_RUN, self._last_run)                       
"""
# configuration example
filtrace:
  name: Filtrace
  action_entity_id: input_boolean.filtrace
  # what will be controlled
  
  timers: { "6:10":50, "10:10":30, "12:00":50, "13:10":2, "15:00":20, "16:00":30, "17:00":20, "17:30":20, "18:00":50, "20:00":30, "21:20":5 }        
  #from timers will be children

  condition: input_boolean.filtrace_timer
  # parent      turnoffon.filtrace
  # children    turnoffon.filtrace_01,....
"""

class CasovacHlavni(TurnonoffEntity):
    """ Parent entity """
    def __init__(self, hass, object_id, name, pocet, cfg):
        """Inicializace hlavni ridici class"""
        super().__init__(hass, object_id, True, name)        
        self._pocet = pocet                                # pocet zadefinovanych casovacu
        self._cfg = cfg                                    # konfigurace v dane domene
        self._hass = hass                                  # uschovani classu hass
        self._active_child_id = None                       # active child
        self._state = STATE_ON  
        self._turn_on = cfg.get(CONF_COMMAND_ON)
        self._turn_off = cfg.get(CONF_COMMAND_OFF)
        self.action_entity_id = cfg.get(CONF_ACTION_ENTITY_ID)
        self.linked_entity_id = cfg.get(CONF_LINKED_ENTITY_ID)
        self._condition = cfg.get(CONF_CONDITION)
        self.force_turn = cfg.get(CONF_FORCE_TURN)        
        
    def _set_on(self, to_do):
        """ Returning if set command """
        return self._turn_on == to_do

    async def reset_timers(self):
        """ Reseting all timers """
        
        for _ , entity in self._hass.data[DOMAIN][O_CHILDREN]:
            my_debug("Reseting timers: {}".format(entity))
            entity.reset_timers(    )

    @property
    def should_poll(self):
        """If entity should be polled."""
        return False

    @property
    def name(self):
        """Navrat nazvu hlavniho casovace"""
        return self._name

    async def set_to_memory(self):
        my_debug("Setting to memory: {}".format(self.entity_id))

    async def regular_loop(self):        
        """ Regular interval for turn_on turn_off """

        if SHUT_DOWN:
            my_debug("Shutting down")
            return

        my_debug("Regular interval: {}".format(self.entity_id))        
        if self._condition != None:
            try:
                entity = self.hass.states.get(self._condition)                
                entity_is_on = is_on(entity)
            except:
                my_debug("Not found conditional entity. Setting to off - nothing will happen")
                entity_is_on = False
            if not entity_is_on:                
                my_debug("Condition {} caused stop calling interval. Next call: {}".format(entity, SCAN_INTERVAL))
                """
                async_track_time_interval(self.hass, self.regular_loop(),
                        datetime.timedelta(seconds=SCAN_INTERVAL))
                """
                async_call_later(self.hass, SCAN_INTERVAL, self.regular_loop())
                return        
        my_debug("Calling service: {} - {} for: {} ".format(DOMAIN, SERVICE_RUN_CASOVAC, self.entity_id))  
        await self.hass.services.async_call(DOMAIN, SERVICE_RUN_CASOVAC, { ATTR_ENTITY_ID: self.entity_id })            
        my_debug("asking for call later after {} seconds".format(SCAN_INTERVAL))        
        """
        async_track_time_interval(self.hass, self.regular_loop(),
                        datetime.timedelta(seconds=SCAN_INTERVAL))
        """
        async_call_later(self.hass, SCAN_INTERVAL, self.regular_loop())
    
    def set_turn_on(self):
        self._state = STATE_ON
        self.async_schedule_update_ha_state()

    def set_turn_off(self):
        self._state = STATE_OFF
        self.async_schedule_update_ha_state()

    @property
    def state(self):
        """Return the state of the component."""
        return self._state

    async def run_casovac(self):        
        """  """
        my_debug("running timer searching")
        self._active_child_id = None

        # It means if state of parent
        if self.state != STATE_ON:
            my_debug("{} is not on. Not seaching".format(self.entity_id))
            return

        my_debug("Searching interval for: {}".format(self.entity_id))

        # Searching for active interval
        i = 1        
        just_now = datetime.datetime.now() 
        tw = datetime.datetime.today().weekday()
        my_debug("Day of week: tw: {}".format(tw))

        while (self._active_child_id == None) and (i <= self._pocet):        
            entity_id = get_child_object_id(self.entity_id, i)
            
            entity = self.hass.states.get(entity_id)
            # Nacitam atributy dane entity
            if (entity == None) :
                my_debug("FATAL! Not found entity: {}".format(entity_id))
                return
            attr = entity.attributes

            start_time = attr[ATTR_START_TIME]
            end_time = attr[ATTR_END_TIME]
            weekdays = attr.get(ATTR_WEEKDAYS)
            
            test_time = True
            if weekdays is not None:
                twd = WEEKDAYS[tw]
                test_time = twd in weekdays

            if test_time and (just_now >= prevedCasPar(start_time, just_now)) and (just_now <= prevedCasPar(end_time, just_now)):        
                my_debug("active entity in period: {}".format(entity_id))                
                self._active_child_id = entity_id
            i += 1

        # V zavislosti je-li v casovem intervalu spoustim prikaz
        if self._active_child_id == None :
            self.to_do = self._turn_off
        else:
            # Bude se nastavovat
            self.to_do = self._turn_on
            _ , entity_id = split_entity_id(self._active_child_id)
            active_object = self.hass.data[DOMAIN][O_CHILDREN][entity_id]
            # active_object = self.hass.states.get(entity_id)
            # investigate
            my_debug(active_object)
            active_object.set_last_run()   # children
            self.set_last_run()            # parent
                
        self.async_schedule_update_ha_state()                        
        return self
    
    def set_time(self, start_time, end_time):
        """ Prazdna funkce v pripade volani pro tuto entitu """ 
        my_debug("FATAL")
        return

    async def async_added_to_hass(self):        
        """Run when entity about to be added."""
        await super().async_added_to_hass()        
        old_state = await self.async_get_last_state()
        if old_state is not None:                        
            self._state  = old_state.state
            
    @property
    def state_attributes(self):
        """Return the state attributes."""
        attrs = {
            ATTR_LAST_RUN: self._last_run,
            ATTR_ACTIVE_CHILD_ID : self._active_child_id
        }
        return attrs
    
            

class Casovac(TurnonoffEntity):
    """Casovac entita pro jednotlive zadefinovane casy."""

    def __init__(self, hass, object_id, name, start_time, end_time, weekdays,force_initial):
        """Inicializace casovac"""
        super().__init__(hass, object_id, True, name)                        
        self._start_time = start_time                         # zacatek casoveho intervalu
        self._end_time = end_time
        self._start_time_init = self._start_time
        self._end_time_init = self._end_time
        self._weekdays = weekdays
        self._force_initial = force_initial
        self._entity_edit_start = None
        self._entity_edit_end = None
        
    def edit_entity(self, edit_start, edit_end) :
        self._entity_edit_start = edit_start
        self._entity_edit_end = edit_end
    
    async def async_added_to_hass(self):        
        """Run when entity about to be added."""
        await super().async_added_to_hass()                
        old_state = await self.async_get_last_state()
        if old_state is not None and not self._force_initial:                        
            self._start_time  = old_state.attributes.get(ATTR_START_TIME, self._start_time)           
            self._end_time  = old_state.attributes.get(ATTR_END_TIME, self._end_time)           
            self._weekdays  = old_state.attributes.get(ATTR_WEEKDAYS, self.weekdays)           
            
    @property
    def should_poll(self):
        """If entity should be polled."""
        return False

    @property
    def name(self):
        """Navrat jmena pro Casovac."""
        return self._name

    @property
    def state(self):
        """Return the state of the component."""
        return "{} - {}".format(self._start_time,  self._end_time)


    @property
    def state_attributes(self):
        """Return the state attributes."""
        attrs = {
            ATTR_START_TIME:        self._start_time,            
            ATTR_END_TIME:          self._end_time,
            ATTR_LAST_RUN:          self._last_run,
            ATTR_START_TIME_INIT:   self._start_time_init,
            ATTR_END_TIME_INIT:     self._end_time_init
        }
        if self._weekdays is not None:
            attrs[ATTR_WEEKDAYS] = self._weekdays
        return attrs

    def reset_timers(self):
        """Reseting time from initialisation"""
        self._start_time = self._start_time_init
        self._end_time = self._end_time_init
        self.async_schedule_update_ha_state()
                
    def set_time(self, start_time, end_time):
        """ Service uvnitr jednotliveho casovace. """        
        my_debug("Setting new time: {} {}".format(start_time, end_time))        
        try:
            if start_time is None:
                start_time = self._start_time
            else:
                self._start_time = time_to_string(start_time)
            
            if end_time is not None:            
                self._end_time = time_to_string(end_time)            
            self.async_schedule_update_ha_state()
        except:
            _LOGGER.error('Set time was not possible')


    def async_run_casovac(self):
        """Not used in this case"""        
        return 

class M_InputDatetime(InputDatetime):
    """ Modified InputDatetime """
    # input_object_id, name_input, start_time, new_object_id, True
    def __init__(self, object_id, name, initial, link_entity, start):
        super().__init__(object_id, name, False, True, None, initial)
        self._link_entity = ENTITY_ID_FORMAT.format(link_entity)
        self._start = start
            
    async def _call_service(self, time_val) :        
        if self._start :            
            my_debug("Start new value: {}".format(time_val))
            await self.hass.services.async_call(DOMAIN, SERVICE_SET_TIME, { ATTR_ENTITY_ID: self._link_entity, ATTR_START_TIME: time_to_string(time_val) }, blocking=True)        
        else :
            my_debug("End new value: {}".format(time_val))
            await self.hass.services.async_call(DOMAIN, SERVICE_SET_TIME, { ATTR_ENTITY_ID: self._link_entity, ATTR_END_TIME: time_to_string(time_val) }, blocking=True)        

    def async_set_datetime(self, date_val, time_val):
        """ Is calling in fire of SERVICE_SET_DATETIME """
        super().async_set_datetime(date_val, time_val)             
        test = time_to_string(time_val)
        if test is not None:
            async_call_later(self.hass, 1, self._call_service(time_val))