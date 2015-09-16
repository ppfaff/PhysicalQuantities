# -*- coding: utf-8 -*-
"""
Created on Fri Aug 28 08:29:29 2015

@author: paulp
"""
from math import log10 as log
from math import pi
from copy import deepcopy
import unittest
import cProfile


class UnitError(Exception):
        pass


class PhysQuant(object):
    """ This Class defines objects with a scalar value and a unit.  It can
    handle simple cases of scaled units.  The object stores the values as SI
    based units, except for mass which is stored as grams (g).  A PhysQuant
    object is instantiated by providing a string that can be interpred as a
    meaningful scalar quantity and a unit or measure.  (Methods are provided to
    change the output unit as a string, to invert the unit and to change the 
    unit by multiplying by a scale factor.) Calling the PhysQuant as a
    @property returns the scalar unit pair as stored. PhysQuant objects support
    some math operations including reciprocals, multiplication with scalars
    or other PhysQuant objects.  In addition Objects can be created with simple
    math operations where 'a/unit' is accepted as is 'a unit-1', or to 
    multiply units in a def 'a unit1.unit2'.  In addition a short hand  pq 
    creator class is useful for converting things to PhysQuant objects.
    Use:
        MyQuant = PhysQuant("input_str")
    Example input_str:
        "100 MOhm"
        "1 uF/cm2"
        "9.8 m/sec2"
        "20 pS"
        "10 mV"
        "10 pF/ 20 um2"
        "100 Ohm.cm"
        
    Physical Quantities are stored as a Dictionary of a primary unit and 
    a unit that is scaling the primary unit.  So:
    
    Key: "num": list of [scalar, [unit strings], and 1] to indicate
                a numerator
         "denom": list of [scalar, [unit strings], -1]  to indicate
                reciprocal unit.  Scalar of denom is normally processed
                to "1.0".
                
    Examples: "1 uF/cm2": {'num': (0.009999999999999998, ['F'], 1),
                          "denom": (1.0, ['m', 'm'], -1) }
              "100 ohm.cm": {'num': (10000.0, ['Ω', 'm'], 1),
                               "denom": (1.0, [], -1) }
    """

    # Class Parameters
    debug = False
    _SI_grams = True
    # Dicitonary of preferred unit values
    better_unit = {"ohm": "Ω", "Ohm": "Ω", "ohms": "Ω", "Ohms": "Ω",
                   "Amp": "A", "amp": "A", "Amps": "A", "amps": "A",
                   "mole": "mol", "moles": "mol", "liter": "l",
                   "Liter": "l", "liters": "l", "L": "l", "second": "sec",
                   "gram": "g", "q": "coul", "Q": "coul"}
    # Dicitonary of potential unit prefixes and their values
    prefix = {"m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15,
              "K": 1.0e3, "M": 1.0e6, "G": 1.0e9, "μ": 1e-6,
              "c": 1e-2, "k": 1e3, "a": 1e-18}

    @classmethod
    def clean_unit(cls, units_dict):
        """ Does cleanup of alternative strings that might have been provided
        to ensure common units are stored in the same way in all dictionaries.
        Also removes prefixes from units and modifies the scalar value
        accordingly.  Ensures that all units are stored in the same way in all
        instances
        """
        tmp_units_dict = deepcopy(units_dict)
        if PhysQuant.debug: 
            print("Enter clean_unit")
            print(units_dict, "NUM", units_dict["num"], "DENOM", units_dict["denom"])
        for key, value in units_dict.items():
            if PhysQuant.debug: print("Units to process", key, len(value), value)
            if len(value) == 3:
                for indx, str_unit in enumerate(value[1]):
                    unit = str_unit
                    if str_unit:
                        if str_unit not in cls.better_unit.values() or str_unit[1:] not in cls.better_unit.values():
                        # if the str_unit is not based on a better_unit string
                        # replace it with the preferred better_unit string
                            for bad_unit in cls.better_unit.keys():
                                # print(key)
                                if PhysQuant.debug: print(str_unit, bad_unit)
                                #if we find a better unit replace the string
                                pos = str_unit.find(bad_unit)
                                if pos >= 0:
                                    unit = str_unit.replace(bad_unit,
                                                        cls.better_unit[bad_unit])
                    value[1][indx] = unit
                    tmp_units_dict[key] = value
                if PhysQuant.debug: print("replaced ", units_dict)
            else:
                print("{0}: {1} not understood in ".format(key, value), units_dict)
        return tmp_units_dict
    
    @classmethod
    def find_prefix(cls, in_scalar, use_centi=False):
        """ Classmethod to generate the appropriate prefix to add and adjust
        the scalar by the appropriate amount.
        """
        output_value = in_scalar
        best_prefix = ""
        for prefix, value in PhysQuant.prefix.items():
            if prefix == "c" and not use_centi:
                continue
            scaled_value = in_scalar / value
            if 0.9 <= scaled_value < 999:
                output_value = scaled_value
                best_prefix = prefix
                break
        return output_value, best_prefix
        
    @classmethod
    def _interpret(cls, *args, **kwargs):
        """ _interpret takes the inputs to PhysQuant and determines how to
        construct the PhysQuant object.  Its primary job is to see what has
        been passed, then send the appropriate information to make_dict, which
        does the actual job of constructing the unit_dict that is at the 
        heart of a PhysQuant Object. Return is temp_dict a dictionary in the
        basic form needed to create the PhysQuant object
        """
        temp_dict = {"num": [1.0, [], 1], "denom": [1.0, [], -1]}
        if PhysQuant.debug: print("Enter _interpret")
        if PhysQuant.debug: print("args {0}, kwargs {1}".format(args, kwargs))

        if args:
            # if non-dictionary object was passed determine what it is. Most
            # times this will be a string that contains a number and a unit.
            # But, we can also handle numbers without a unit and PhysQuant
            # objects to make a copy of the object.  Turning numbers into
            # PhysQuant objects allows an easy way to do multiplication using 
            # normal math * since PhysQuant objects have a defined __mul__().

            var = args[0]
            if isinstance(var, str):
                # Two types of strings can be handled, repr() type strings that
                # can be interpreted as unit_dict definitions, and strings
                # of the unit = scalar type.
                if PhysQuant.debug: print("An args string")
                if var[:2] == "**":
                    # If we have a keyword string dict definition in under the
                    # args input, process it if possible.  First remove "**"
                    kwargs_def = var[2:]
                    if PhysQuant.debug: print("An args kwargs", kwargs_def)
                    # Then convert string to a dictionary object
                    kwargs = eval(kwargs_def)
                    if PhysQuant.debug: print("kwargs {0}, type: {1}".format(
                                              kwargs, type(kwargs)))
                    for key, value in kwargs.items():
                        # Then prepare it for use if possible

                        if key in ["num", "denom"]:
                            temp_dict[key] = PhysQuant.conform_list(value)
                        else:
                            raise ValueError("{0}: {1} is not a unit_dict".format(key, value))
                else:
                    # Otherwiese we have a string definition of a scalar, unit
                    temp_dict = PhysQuant._make_dict(var)
            elif isinstance(var, PhysQuant):
                # if the args is a PhysQuant, then clone its dictionary to make
                # a new PhysQuant object
                temp_dict = var._unit_dict
            elif isinstance(var, float) or isinstance(var, int):
                # if a number was passed, convert it to a PhysQuant type object
                # to allow multiplicaiton with PhysQuants
                temp_dict = {"num": [var, [], 1], "denom": [1.0, [], -1]}
            else:
                raise ValueError("{0} is not understood".format(args))
        if kwargs:
            # Two types of Kwargs, one is a unit_dict definition and the other
            # is a unit=scalar pair.  
            temp_dict = {"num": [1.0, [], 1], "denom": [1.0, [], -1]}
            holding_dict = {}
            # Keywords need to define a numerator, denominator or both
            if PhysQuant.debug: print("A kwargs input", kwargs)
            for key, value in kwargs.items():
                if key == "num" or key == "denom":
                    # Make sure unti_dict items are properly configured
                    if isinstance(value, str):
                        if key == "num":
                            holding_dict = PhysQuant._make_dict(value)
                            temp_dict["num"] = holding_dict["num"]
                        if key == "denom":
                            holding_dict = PhysQuant._make_dict("1/" + value)
                            temp_dict["denom"] = holding_dict["denom"]
                    elif isinstance(value, (list, tuple)):
                        temp_dict[key] = PhysQuant.conform_list(value)
                    else:
                        raise ValueError("{0}: {1} is not a valid unit_dict def".format(key, value))

                else:
                    # if it is not a unit dict item it is a keyword definition
                    # of a unit.  Turn it to a string and allow PhysQuant to 
                    # make the unit_dict
                    unit_str = str(value) + " " + str(key)
                    temp_dict = PhysQuant._make_dict(unit_str)
                
        if PhysQuant.debug: print(temp_dict)
        return temp_dict

    @classmethod
    def _make_dict(cls, unit_str):
        """ Runs through the steps to create a unit_dict from a unit_string"""
        if PhysQuant.debug: print("Enter _make_dict")
        temp_dict = PhysQuant.id_scaled_unit(unit_str)
        if PhysQuant.debug: print("id_scaled_dict", temp_dict)
        temp_dict = cls.clean_unit(temp_dict)
        if PhysQuant.debug: print("clean_unit_dict", temp_dict)
        temp_dict = cls.replace_prefix(temp_dict)
        if PhysQuant.debug: print("replaced_prefix_dict", temp_dict)
        temp_dict = PhysQuant.normalize_denom(temp_dict)
        if PhysQuant.debug: print("normalized_dict", temp_dict)
        return temp_dict


    @classmethod
    def _multiply_unit_dicts(cls, pq1, pq2):
        """ Multiplies the contents of two PhysQuant unit_dict together by
        multiplying the scalar values and joining the units for the two
        dictionaries.  Returns the combined unit_dict.  Can take as input
        either two unit_dict or two PhysQuant objects or two things that can
        be interpreted to be PhysQuant objects.
        """
        temp_dict_product = {}
        # Gathers the two unit_dict dictionaries to multiply together
        if isinstance(pq1, PhysQuant):
            temp_dict_pq1 = deepcopy(pq1.unit_dict)
        elif isinstance(pq1, dict):
            temp_dict_pq1 = deepcopy(pq1)
        else:
            # strings, floats, int...
            try:
                temp_pq1 = pq(pq1)
                temp_dict_pq1 = deepcopy(temp_pq1)
            except:
                raise ValueError("{0} is not a good PhysQuant".format(pq1))

        if isinstance(pq2, PhysQuant):
            temp_dict_pq2 = deepcopy(pq2.unit_dict)
        elif isinstance(pq2, dict):
            temp_dict_pq2 = deepcopy(pq2)
        else:
            try:
                temp_pq2 = pq(pq2)
                temp_dict_pq2 = deepcopy(temp_pq2)
            except:
                raise ValueError("{0} is not a good PhysQuant".format(pq2))
        
        # Processes the dictionaries by muptiplying the scalar values for the
        # numerator and denominator and combining the units.  First checks to
        # see if power is compatible otherwise something is amiss
        for key, value in temp_dict_pq1.items():
            if value[2] == temp_dict_pq2[key][2]:
                power = value[2]
            else:
                raise ValueError("powers of pq1.{0}={1} and pq2.{0}={2} not compatible".format(key, value, temp_dict_pq2[key]))
            out_scalar = value[0] * temp_dict_pq2[key][0]
            unit = deepcopy(value[1])
            unit.extend(temp_dict_pq2[key][1])
            temp_dict_product[key] = [out_scalar, unit, power]
        return temp_dict_product

    @classmethod
    def replace_prefix(cls, units_dict):
        """ This method removes the prefixes from units and adjusts the scalar
        associated with that unit by the appropriate amount.  If the unit is
        a squared or cubed unit, the prefix is extracted and the
        prefix is raised to the appropriate power.  If it is a temp unit in
        Celsius (C or oC) or Fahrenheit (oF) it is converted to K.  Kelvin (K)
        must be entered without degrees or prefix.
        Input: Dictionary of list [scalar, unit with prefix, power]
        Output: Dictionary of list [scaled scalar, unit w/o prefix, power]
        """
        tmp_units_dict = deepcopy(units_dict)
        #print("tmpunitsdict", tmp_units_dict)
        prefix_value = 1.0        
        if PhysQuant.debug: print("Enter replace_prefix")    
        for key, value in units_dict.items():
            if PhysQuant.debug: print("Unit0", value[0], type(value[0]),
                                      "Unit1", value[1], type(value[1]),
                                      "Unit3", value[2], type(value[2]))
            # Temp variables are assigned to the tuple contents
            unit_value = float(value[0])
            units = value[1]
            unit_power = value[2]
            if units:
                for index, unit in enumerate(units):
                    if unit in PhysQuant.better_unit.values():
                        # if we have a preferred unit, leave it alone
                        continue
                    """ If a unit is present and it is longer than 1, so it might have 
                    a prefix, then the 1st character is scanned against the dict
                    of unit prefixes.  If a prefix is found it is used to process the
                    unit value into a string.  Eventually we will evaluate the term
                    in the unit_value using eval() to generate a float"""
                    if unit and len(unit) > 1:
                        for prefix, scale in PhysQuant.prefix.items():
                            if PhysQuant.debug: print("Key Test", prefix, unit,
                                                      unit.startswith(prefix))
                            # if the 1st char matches a prefix in the dictionary...
                            if unit.startswith(prefix):
                                if prefix == "m" and unit == "mol":
                                    continue
                                else:
                                    unit = unit.replace(prefix, "")
                                    units.pop(index)
                                    units.insert(index, unit)
                                    if PhysQuant.debug: print("replaced", unit)
                                    prefix_value = scale
                                    break
                        unit_value *= prefix_value
                        if PhysQuant.debug: print(unit_value, unit)
                    # String with math expression for the scalar is evaluated to make
                    # a float scalar.  The results are packaged into a tuple for
                    # placement back in the dictionary
                    if unit in ("oC", "C", "Celsius", "oF", "Fahrenheit"):
                        unit_value = PhysQuant.convert_to_kelvins(unit_value, unit)
                        unit = "K"
                        units.pop(index)
                        units.insert(index, unit)
                new_unit_list = [unit_value, units, unit_power]
                tmp_units_dict[key] = new_unit_list
                #print("Temp_unit", key, new_unit_list, tmp_units_dict)
        return tmp_units_dict

    def __init__(self, *args, **kwargs):
        """This is the internal dictionary containing the info for the Physical
        Quantity that is represented in this Class. It is hidden from the 
        Outside and its values are retrieved using unit property.
        """

        self._unit_dict = PhysQuant._interpret(*args, **kwargs)

    @property
    def prefixed(self):
        """The primary method to access the number and unit in the PhysQuant
        Hidden dictionary _unit_dict as a properly prefixed unit.  
        Output is a tuple composed of the value as a float and the appropriate
        prefixed unit.
        """
        use_centi = False
        self.reduce
        self._unit_dict = self.normalize_denom(self.unit_dict)
        unit_scalar = self.unit_dict["num"][0]
        if "m" in self.unit_dict["num"][1]:
            # Only use centi prefix on meters units
            use_centi = True
        output_value, to_add_prefix = self.find_prefix(unit_scalar, use_centi)
        num_string = PhysQuant.prefixed_list_to_string(to_add_prefix,
                                                      self.unit_dict["num"][1])
        denom_string = PhysQuant.prefixed_list_to_string("",
                                                    self.unit_dict["denom"][1])
        if denom_string:
            output_unit = num_string + "/" + denom_string
        else:  
            output_unit = num_string
        if PhysQuant.debug: print("unit Output", output_value, output_unit)
        return output_value, output_unit
        
    @property
    def reduce(self):
        """ reduct cancels units in the numerator and denominator"""
        temp_denom_unit_list = list(self._unit_dict["denom"][1])
        # First check if ohms or S in denom unit list and if so put reciprocal
        # unit in the num unit list
        for unit in self._unit_dict["denom"][1]:
            if unit in ("Ω", "S"):
                temp_denom_unit_list.remove(unit)
                if unit == "Ω":
                    self._unit_dict["num"][1].append("S")
                else:
                    self._unit_dict["num"][1].append("Ω")
        # Now cancel any units present in both the num and denom unit lists
        self._unit_dict["denom"][1] = temp_denom_unit_list
        temp_num_unit_list = list(self._unit_dict["num"][1])
        for unit in self._unit_dict["denom"][1]:
            cnt = temp_num_unit_list.count(unit)
            if cnt >= 1:
                temp_denom_unit_list.remove(unit)
                temp_num_unit_list.remove(unit)
        numerator = [self._unit_dict["num"][0], temp_num_unit_list,
                     self._unit_dict["num"][2]]
        denominator = [self._unit_dict["denom"][0], temp_denom_unit_list,
                       self._unit_dict["denom"][2]]
        self._unit_dict["num"] = numerator
        self._unit_dict["denom"] = denominator

    @property
    def scalar(self):
        """ Returns the internal scalar stored in the unit_dict.  However if
        flag SI_grams=False, convers g to kg by dividing by 1000.0
        """
        stored_scalar = self._unit_dict["num"][0]
        if not self._SI_grams and self._unit_dict["num"][1] == 'g':
            stored_scalar = stored_scalar / 1000.0
        return stored_scalar

    @property
    def unitless(self):
        """ Returns the internal scalar stored in the unit_dict only if there
        are no units remaining in the unit_dict
        """
        stored_scalar = self._unit_dict["num"][0]
        if not self.unit_dict["num"][1] and not self.unit_dict["denom"][1]:
            return stored_scalar
        else:
            raise ValueError("Scalar still has attached Units")
        
    @property
    def SI(self):
        """ Returns the internal SI type unit stored in the unit_dict along
        with its scalar value.
        SI will return grams if the hidden class level flag _SI_grams
        is set to True, otherwise returns kg.
        """
        output_unit = ".".join(self._unit_dict["num"][1])
        scale_unit = ".".join(self._unit_dict["denom"][1])
        local_scalar = self._unit_dict["num"][0]
        if self._unit_dict["denom"][2] == -1 and self._unit_dict["denom"][1]:
            output_unit = output_unit + "/ " + scale_unit
        if not self._SI_grams and self._unit_dict["num"][1] == 'g':
            output_unit = "kg"
            local_scalar = local_scalar / 1000.0
        return local_scalar, output_unit

    @property
    def unit_dict(self):
        return self._unit_dict

    @property
    def unitless(self):
        """ Returns the internal scalar stored in the unit_dict only if there
        are no units remaining in the unit_dict
        """
        stored_scalar = self._unit_dict["num"][0]
        if not self.unit_dict["num"][1] and not self.unit_dict["denom"][1]:
            return stored_scalar
        else:
            raise ValueError("Scalar still has attached Units")
        
    def __call__(self, var):
        #def __call__(self):
        """Call can make a new PhysQuant object the same as using pq"""
        if PhysQuant.debug: print("Enter __call__")    
        #return self.scalar, self.SI
        return PhysQuant(var)


    def __add__(self, pq_obj):
        """ redefines addition for PhysQuant objects.  Method adds the scalar
        values if the unit_lists are the same.  Otherwise the method fails.
        Both objects must be PhysQuant objects or a ValueError is raised.
        """

        if PhysQuant.debug: 
            print("add", self.unit_dict, pq_obj.unit_dict)
        try:
            self.melt
            self.reduce
            pq_obj.melt
            pq_obj.reduce
            temp_unit_dict = self.unit_dict
            my_temp_denom_unit_list = list(self._unit_dict["denom"][1])
            pq_obj_temp_denom_unit_list = list(pq_obj._unit_dict["denom"][1])
            my_temp_num_unit_list = list(self._unit_dict["num"][1])
            pq_obj_temp_num_unit_list = list(pq_obj._unit_dict["num"][1])
            if my_temp_denom_unit_list == pq_obj_temp_denom_unit_list and my_temp_num_unit_list == pq_obj_temp_num_unit_list:
                scalar_sum = self.unit_dict["num"][0] + pq_obj.unit_dict["num"][0]
                temp_unit_dict["num"][0] = scalar_sum
                return pq(**temp_unit_dict)
        except ValueError as e:
            e("PhysQuant Object units are not identical")
 
    def __mul__(self, multiplier):
        """ redefines multiplication for PhysQuant objects if PhysQuant is the
        item preceding the "*" operator.  Method multiplies the scalar values
        and joins the unit lists for the unit_dict and returns this as a 
        new PhysQuant object  Any units in the numerator and denominator are
        cancelled.If one of the objects is not a PhysQuant object a
        conversion is attempted as a first step in the process
        """
        if PhysQuant.debug: 
            print("Multiply by", multiplier)
        if isinstance(multiplier, (int, float)):
            multiplier = pq(multiplier)
        
        the_dict = PhysQuant._multiply_unit_dicts(self.unit_dict,
                                                   multiplier.unit_dict)
        pq_prod = pq(**the_dict)
        pq_prod.melt
        pq_prod.reduce
        return pq_prod

    def __pow__(self, exponent):
        """ redefines exponentiation for PhysQuant objects.  Basically raises
        the scalar in the numerator by the supplied power then creates a unit
        list that is repeted exponent number of times.
        """
        if PhysQuant.debug: 
            print("Multiply by", multiplier)
        if isinstance(exponent, (int, float)):
            temp_dict = deepcopy(self._unit_dict)
            ratio = temp_dict["num"][0] / temp_dict["denom"][0]
            temp_dict["num"][0] = ratio ** exponent
            temp_dict["denom"][0] = 1.0
            denom_unit_list = temp_dict["denom"][1]
            temp_dict["denom"][1] = denom_unit_list * exponent
            num_unit_list = temp_dict["num"][1]
            temp_dict["num"][1] = num_unit_list * exponent
            pq_prod = pq(**temp_dict)
            pq_prod.melt
            pq_prod.reduce
            return pq_prod
        else:
            raise ValueError("Exponent must be a float or int")

    def __rmul__(self, multiplier):
        """ redefines multiplication for PhysQuant objects if PhysQuant is the
        item following the "*" operator.  Method multiplies the scalar values
        and joins the unit lists for the unit_dicts and returns this as a 
        new PhysQuant object  Any units in the numerator and denominator are
        cancelled.  If one of the objects is not a PhysQuant object a
        conversion is attempted as a first step in the process
        """
        if PhysQuant.debug: 
            print("Multiply by", multiplier)
        if isinstance(multiplier, (int, float)):
            multiplier = pq(multiplier)
        the_dict = PhysQuant._multiply_unit_dicts(self.unit_dict,
                                                   multiplier.unit_dict)
        pq_prod = pq(**the_dict)
        pq_prod.melt
        pq_prod.reduce
        return pq_prod
       
    def __repr__(self):
        """This produces a string representation of the unit and scalar stored
        in this object. It works the same as self.prefix property above except
        it produces a string output with prefixed units.  It is primarily used
        for producing nice string outputs using iPython.
        """
        if PhysQuant.debug: print("Enter __repr__")    
        stored_scalar, unit = self.prefixed
        if PhysQuant.debug: print("__str__ unit Output", stored_scalar, unit)

        return "{0:.3f} {1}".format(stored_scalar, unit)  


    def __str__(self):
        """This produces a string representation of the unit and scalar stored
        in this object. It works the same as self.prefix property above except
        it produces a string output with prefixed units.  Primarily used for
        print outputs.  Currently produces the same output as __repr__() but
        could be defined differently in the future if desired
        """
        if PhysQuant.debug: print("Enter __str__")    
        stored_scalar, unit = self.prefixed
        if PhysQuant.debug: print("__str__ unit Output", stored_scalar, unit)
        return "{0:.3f} {1}".format(stored_scalar, unit)  

    def _assign_prefix(self, number):
        """ This function determines the proper prefix to use for a number.  
        amt return is between 1 - 1000 with the unit prefix.  If the quantity
        is below 1e-18 then we will call it zero.
        
        Input: floating point number
        Output: floating point number scaled, with the appropriate unit prefix
        """
        if PhysQuant.debug: print("Enter _assign_prefix")    
        if abs(number) < 1e-18:
            amt = 0
            prefix_to_use = ""
        else:
             # Returns the number's integer power of 10
            log_numb = int(log(abs(number)))
            my_prefix = {-3: "m", -6: "μ",
                         -9: "n", -12: "p",
                         -15: "f", 3: "K", 0: ""}
            # This loop finds the prefix that displays the value as a number
            # Greater than 1 and less than 1000
            for power in my_prefix.keys():
                diff = log_numb - power
                if 0 <= diff < 3:
                    prefix_to_use = my_prefix[power]
                    amt = number / (10**power)
                    break
        if PhysQuant.debug: print(amt, prefix_to_use)
        return amt, prefix_to_use
    
    def change_unit(self, new_unit_str, with_prefix=False):
        """ This method allows a user to print out a stored Physical Quantity
        in a different compatible unit.  It is primarily useful for scaled
        parameters, where for example you can convert from x/m to 100x/cm.
        
        Input: String unit representation of how you would like the output 
        returned. Examples:  "F/cm2", "F/um2"
        Output: String printout of the value in the desired unit with the 
        proper prefix on the top unit.  Example: parameter is 25 mF/m2. Returns
        in F/cm2 as 25 μF/cm2 or in F/μm2 as 25 fF/μm2"""
        if PhysQuant.debug: print("Enter change_unit")    
        change_unit_dict = {}
        temp_unit_dict = {}
        # Make a copy of the new_unit_str
        process_str = new_unit_str[:]
        # Run through _interpret method to get out the dict for the new unit.
        change_unit_dict = self._interpret(process_str)
        if PhysQuant.debug: print("New_Dict", change_unit_dict)
        # Check to see if the we have a compatible unit conversion.  If so
        # then run the conversion to get the scalar rescaled into the new unit
        # Then run assign_prefix to get the returned prefix correct.        
        if self._unit_dict["num"][1] == change_unit_dict["num"][1] and self._unit_dict["denom"][1] == change_unit_dict["denom"][1]:
               rescaled = self._unit_dict["num"][0] / change_unit_dict["num"][0]
               temp_unit_dict["num"] = (rescaled, process_str, 1)
               if with_prefix:
                   scaled, prefix_to_add = self._assign_prefix(temp_unit_dict["num"][0])
                   # Produces a formatted string output
                   return scaled, prefix_to_add + process_str
               else:
                   return temp_unit_dict["num"][0], process_str
        else:
            print("Conversion not Compatible")
            return None

    def freeze(self):
        """ This method converts the dictionary entries into immutable tuples
        in order to keep important constants from being accidentally
        redefined.
        """

        temp_frozen_unit_dict = {}
        temp_frozen_unit_dict = self.unit_dict
        #print("pq_in", pq_in.unit_dict)
        frozen_num_units = tuple(temp_frozen_unit_dict["num"][1])
        frozen_denom_units = tuple(temp_frozen_unit_dict["denom"][1])
        temp_num_tuple = (temp_frozen_unit_dict["num"][0], frozen_num_units,
                          temp_frozen_unit_dict["num"][2])
        temp_denom_tuple = (temp_frozen_unit_dict["denom"][0], frozen_denom_units,
                          temp_frozen_unit_dict["denom"][2])
        temp_frozen_unit_dict["num"] = temp_num_tuple
        temp_frozen_unit_dict["denom"] = temp_denom_tuple
        self._unit_dict = temp_frozen_unit_dict

    def inverted(self):
        """ Returns an inverted version of the unit_dict in this instance for
        use in performing division by multiplying with an inverted unit_dict.
        Does not change the unit_dict in this instance.  For ohms and siemens,
        converts the unit to its reciprocal unit
        """
        if PhysQuant.debug: print("Enter invert")    
        inverted = False
        # Creates a deepcopy to make sure we don't mess with self.unit_dict
        temp_dict = deepcopy(self.unit_dict)
        for key, value in temp_dict.items():
            if value[1] == "Ω":
                factor = 1.0 / value[0]
                unit_value = "S"
                inv_tuple = (factor, unit_value, value[2])
                temp_dict[key] = inv_tuple
                inverted = True
                break
            elif value[1] == "S":
                factor = 1.0 / value[0]
                unit_value = "Ω"
                inv_tuple = (factor, unit_value, value[2])
                temp_dict[key] = inv_tuple
                inverted = True
                break
        scale_unit = temp_dict["denom"][1]
        scale_power = temp_dict["denom"][2]
        unit_list = temp_dict["num"]
        #print("scales", scale_unit, scale_power)
        invert_power = -unit_list[2]
        new_list = (unit_list[0], unit_list[1], invert_power)
        #print("new_tuple", new_list)
        temp_dict["denom"]= new_list
        temp_dict["num"] = (1, scale_unit, -scale_power)
        inv_pq = pq(**temp_dict)
        inv_pq._unit_dict = inv_pq.normalize_denom(temp_dict)
        
        return inv_pq

    def melt(self):
        """ This method converts the dictionary entries into mutable lists in
        case they are unmutable tuples
        """
        temp_melt_unit_dict = {}
        temp_melt_unit_dict = self.unit_dict
        #print("pq_in", pq_in.unit_dict)
        melt_num_units = list(temp_melt_unit_dict["num"][1])
        melt_denom_units = list(temp_melt_unit_dict["denom"][1])
        temp_num_list = [temp_melt_unit_dict["num"][0], melt_num_units,
                          temp_melt_unit_dict["num"][2]]
        temp_denom_list = [temp_melt_unit_dict["denom"][0], melt_denom_units,
                          temp_melt_unit_dict["denom"][2]]
        temp_melt_unit_dict["num"] = temp_num_list
        temp_melt_unit_dict["denom"] = temp_denom_list
        self._unit_dict = temp_melt_unit_dict

    @staticmethod
    def add_prefix(in_scalar, unit_str):
        """ Utility function to convert a scalar and base unit to a scaled
        scalar and prefixed unit.  Only uses centi for length dimensions.
        Can be used separately from class instance to perform these
        conversions.  Not needed for anything in this class, and so could be
        removed
        """
        use_centi = False
        if unit_str == "m" or "m." in unit_str:
            use_centi = True
        output_value, out_prefix = PhysQuant.find_prefix(in_scalar, unit_str)
        return output_value, out_prefix + unit_str

    @staticmethod
    def combine_repeat_unit_as_power(unit_list):
        """ Helper function that returns the unit list with units that are 
        multiplied together as a power of the unit. So, ['m', 'm'] is converted
        to ['m2'].  This is primarily used for formatting for outputs
        """
        temp_unit_list = []
        if unit_list:
            # slicing creates a new unlinked verion of the input unit_list
            temp_unit_list = unit_list[:]
            for unit in unit_list:
                # count the occurances of a unit in the temp_unit_list and if
                # count is greater than 1, remove these units and replace with
                # the power version.  Note, the for loop cycles on the original
                # unit list to avoid indexing problems created by looping on
                # a list that is having elements added and removed
                cnt = temp_unit_list.count(unit)
                if cnt > 1:
                    for i in range(cnt):
                        temp_unit_list.remove(unit)
                    temp_unit_list.append(unit + str(cnt))
        return temp_unit_list

    @staticmethod
    def convert_to_kelvins(in_scalar, temp_unit):
        # converts input temp unit string to a sting that evaluates in Kelvins
        toKelvins = in_scalar        
        if PhysQuant.debug: print("Enter convert_to_kelvins")    
        if temp_unit in ("oC", "C", "Celsius"):
            toKelvins = in_scalar + 273.15
        elif temp_unit in ("oF", "Fahrenheit"):
            toKelvins = (5.0 / 9.0) * (in_scalar -32.0) + 273.15
        return toKelvins

    @staticmethod
    def id_scaled_unit(str_unit):
        """ Input unit string parsing function.  First parses on "/" to split
        into unit and denom parts.  If compound unit will split at "*"
        Returns the unit and denom tuples in an dictionary"""
        if PhysQuant.debug: print("Enter id_scaled_unit")    
        scaled_by_list = []
        str_unit_list = []
        if "/" in str_unit:
            # Split into numerator and denominator if necessary
            scale_base_list = [unit.strip() for unit in str_unit.split("/")]
            # Adding the power to end to indicate numerator or denominator
            str_unit_list = scale_base_list[0].split(" ")
            str_unit_list.append(1)
            scaled_by_list = scale_base_list[1].split(" ")
            scaled_by_list.append(-1)
            if PhysQuant.debug: 
                print("num", scale_base_list, str_unit_list, scaled_by_list)
            if PhysQuant.debug: 
                print("denom", scaled_by_list, len(scaled_by_list),
                                      scaled_by_list[0][0].isnumeric())
            # If numerator or denominator only had one term, check to see if
            # it was a number or a unit and place accordingly
            if len(scaled_by_list) == 2 and scaled_by_list[0][0].isnumeric():
                # if denominator only has a number
                scaled_by_list = [float(scaled_by_list[0]), [],
                                  scaled_by_list[1]]
            elif len(scaled_by_list) == 2:
                # if denominator only has a unit string put 1 in scalar of denom
                # and parse the unit string if more than 1 unit multiplied
                scaled_by_list = [1.0, PhysQuant.parse_unit_string(scaled_by_list[0]), scaled_by_list[1]]
            else:
                scaled_by_list[0] = float(scaled_by_list[0])
                scaled_by_list[1] = PhysQuant.parse_unit_string(scaled_by_list[1])

            if len(str_unit_list) == 2 and str_unit_list[0][0].isnumeric():
                str_unit_list = [float(str_unit_list[0]), [], str_unit_list[1]]
            elif len(str_unit_list) == 2:
                str_unit_list = [1.0, PhysQuant.parse_unit_string(str_unit_list[0]), str_unit_list[1]]
            else:
                str_unit_list[0] = float(str_unit_list[0])
                str_unit_list[1] = PhysQuant.parse_unit_string(str_unit_list[1])
                
        else:
            str_unit_list = str_unit.split(" ") + [1]
            # Mock denominator created since none given
            scaled_by_list = [1.0, [], -1]
            if len(str_unit_list) == 2 and str_unit_list[0][0].isnumeric():
                # Case where only a number and no unit passed
                str_unit_list = [float(str_unit_list[0]), [], str_unit_list[1]]            
            elif len(str_unit_list) == 2 :
                # Case where only a unit and no scalar passed
                str_unit_list = [1.0, PhysQuant.parse_unit_string(str_unit_list[0]), str_unit_list[1]]            
            else:
                # Got everything so just make a list from the unit string
                str_unit_list[1] = PhysQuant.parse_unit_string(str_unit_list[1])            
            
            for index, value in enumerate(str_unit_list[1]):
                if value.endswith("-1"):
                    # If unit in numerator has -1 power move to denominator after
                    # removing the -1 power.  Scalar stays in denominator
                    scaled_by_list.append(value[:-2])
                    str_unit_list.remove(index)
            for index, value in enumerate(scaled_by_list[1]):
                if value.endswith("-1"):
                    # If unit in numerator has -1 power move to denominator after
                    # removing the -1 power.  Scalar stays in denominator
                    str_unit_list.append(value[:-2])
                    scaled_by_list.remove(index)
        return {"num": str_unit_list, "denom": scaled_by_list}

    @staticmethod
    def normalize_denom(units_dict):
        """ This function converts the scalar value associated with a "scaling"
        unit to 1 by dividing this scalar into the "num" scalar
        Input: A dictionary with a "denom" and a "num" entry pointing to
            a list of (scalar, unit, power).
        Output: The same dictionary with the scalar for "denom" divided into
            the "denom" and "num" scalar terms.
        """
        if PhysQuant.debug: print("Enter normalize_denom", units_dict)    
        scaled = units_dict["num"][0] / units_dict["denom"][0]
        units_dict["num"] = [scaled, units_dict["num"][1],
                              units_dict["num"][2]]
        units_dict["denom"] = [1.0, units_dict["denom"][1],
                                 units_dict["denom"][2]]
        return units_dict

    @staticmethod
    def parse_unit_string(unit_str):
        """ Helper function that splits units that are multiplied together
        into a list of units in the numerator or denominator.  Units are
        multiplied together by using the "." operator.  So, "8.314 J/mol.K" is
        the way to enter the gas constant  This function just splits the string
        on the ".".  Note this means that unit names cannot contain a "."
        """
        unit_str_list = []
        if unit_str:
            unit_str_list = unit_str.split(".")
            #print(unit_str, unit_str_list)
            for ind, unit in enumerate(unit_str_list):
                if unit[-1].isnumeric() and float(unit[-1]) > 1.0:
                    end_n = float(unit[-1])
                    unit_str_list.pop(ind)
                    for i in range(int(end_n)):
                        unit_str_list.append(unit[:-1])
        return unit_str_list
            
    @staticmethod
    def remove_prefix(scalar, str_unit):
        """ Staticmethod to remove the prefix from a unit and adjusts the scalar
        associated with that unit by the appropriate amount.  If the unit is
        a squared or cubed unit, the prefix is extracted and the
        prefix is raised to the appropriate power.  If it is a temp unit in
        Celsius (C or oC) or Fahrenheit (oF) it is converted to K.  Kelvin (K)
        must be entered without degrees or prefix.
        Input: something that looks like a float and a prefixed unit
        Output: float and unprefixed unit
        """
        unit_value = float(scalar)
        if PhysQuant.debug: print("Enter replace_prefix")    
        # if unit is already SI or one char or less, then nothing to do        
        if str_unit in PhysQuant.better_unit.values() or len(str_unit) < 2:
            return unit_value, str_unit

        """ If a unit str is longer than 1, it might have 
        a prefix, so the 1st character is scanned against the dict
        of unit prefixes.  If a prefix is found it is removed and the 
        value multiplied against the scalar"""
        if str_unit and len(str_unit) > 1:
            for key, power in PhysQuant.prefix.items():
                if PhysQuant.debug: print("Key Test", key, power,
                                          str_unit.startswith(key))
                # if the 1st char matches a prefix in the dictionary...
                if str_unit.startswith(key):
                    str_unit = str_unit.replace(key, "")
                    if PhysQuant.debug: print("replaced", str_unit)
                    unit_value *=  power
                    break
            if PhysQuant.debug: print(unit_value, str_unit)
        # String with math expression for the scalar is evaluated to make
        # a float scalar.  The results are packaged into a tuple for
        # placement back in the dictionary
        if str_unit in ("oC", "C", "Celsius", "oF", "Fahrenheit"):
            unit_value = PhysQuant.convert_to_kelvins(unit_value, str_unit)
            str_unit = "K"
        return unit_value, str_unit

    @staticmethod
    def prefixed_list_to_string(prefix_to_add, unit_list):
        """ Helper function that can add a prefix to a string representing
        the multiplication of units together.  This function bascially is the
        reverse of the parse_unit_string function
        """
        combined_unit_list = PhysQuant.combine_repeat_unit_as_power(unit_list)
        return prefix_to_add + ".".join(combined_unit_list)

    @staticmethod
    def conform_list(in_list):
        """ This method forces lists to conform to the type needed to properly
        instantiate a new PhysQuant for "num" or "denom"""
        temp_list = []
        if PhysQuant.debug: print("In conform_list", in_list)
        if len(in_list) == 3:
            temp_list = list(in_list)
            temp_list[1] = list(in_list[1])
        else:
            raise ValueError("Entered invalid unit_dict list {0}".format( in_list))
        return temp_list

class rnd_cell(PhysQuant):
    """ Creates a round cell object when given a diameter.  Provides easy
    access to volume, surface area and membrane capacitance for a standard
    cell
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __call__(self):
        """ call takes the diam and converts it to a pq if it isn't already. 
        diam can be an valid term that can be interpreted as a pq, like
        srings, floats,integers, and other PhysQuant items.  Returns a pq
        object for the Surface Area and the Volume"""
        SA = pi * pq(self.__repr__()) ** 2
        Vol = (pi / 6.0)* (pq(self.__repr__()))**3
        return SA, Vol
    
    @property
    def vol(self):
        return (pi / 6.0)* (pq(self.__repr__()))**3
    
    @property
    def sa(self):
        return pi * pq(self.__repr__()) ** 2

    @property
    def cm(self):
        return self.sa * pq("1 uF/cm2")
        
class segment(PhysQuant):
    """ Creates a cylindrical cell object when given a diameter and a length
    as pq objects. Provides easy  access to volume, surface area, membrane 
    capacitance and internal resistance.  cm can be flagged for mylenation
    """
    def __init__(self, myelin=False, **kwargs):
        self._l = kwargs["l"]
        self._d = kwargs["d"]
        self._myelin = myelin
        self.ra_cm = pq("100 ohm.cm")

    def __call__(self):
        """ call takes the diam and converts it to a pq if it isn't already. 
        diam can be an valid term that can be interpreted as a pq, like
        srings, floats,integers, and other PhysQuant items.  Returns a pq
        object for the Surface Area and the Volume"""
        SA = ((pi) * pq(self._d)) * self._l
        Vol = ((pi / 4.0)* (pq(self._d))**2) * self._l
        return SA, Vol

    @property
    def l(self):
        return self._l
    
    @property
    def d(self):
        return self._d

    @property
    def myelin(self):
        return self._myelin

    @myelin.setter
    def myelin(self, myl):
        if myl:
            self._myelin = True
        else:
            self._myelin = False    
        
    @property
    def vol(self):
        return ((pi / 4.0)* (pq(self._d))**2) * pq(self._l)
    
    @property
    def sa(self):
        return ((pi) * pq(self._d)) * pq(self._l)

    @property
    def cm(self):
        if self._myelin:
            cm_s = "0.0167 uF/cm2"
        else:
            cm_s = "1 uF/cm2"
        return self.sa * pq(cm_s)

    @property
    def ra(self):
        inv_vol = self.vol.inverted()
        return inv_vol * self.ra_cm * self.sa

def pq(*args, **kwargs):
    return PhysQuant(*args, **kwargs)

# This code defines pq object constants that can be used after PhysQuant
# is imported

N= pq("6.0224e23 / mol")
R = pq("8.314 J.mol/K")
VtoBase = pq("1.0 J/V.coul")
StoBase = pq("1.0 coul.coul/J.sec.S")
RtoBase = StoBase.inverted()
AtoBase = pq("1.0 coul/sec.A")
F = pq("96500 coul/mol")
tau_conv = pq("1.0 sec/ohm.F")
to_sec = pq("1.0 sec/s")


if __name__ == "__main__":
    """MyQuant = PhysQuant("100 mS/50 cm2")
    print(MyQuant.prefixed)
    print("First Unit_dict", MyQuant.unit_dict)
    print(MyQuant)
    print(MyQuant.change_unit("S/cm2"))
    print("Second Unit_dict", MyQuant.unit_dict)
    print(MyQuant.scalar, MyQuant.SI)
    MyQuant.multiply("100 um2")
    print(MyQuant.prefixed)
    print("Multiplied Unit_dict", MyQuant.unit_dict)
    MyQuant.invert()
    print("Inverted Unit_dict", MyQuant.unit_dict)
    print(MyQuant.prefixed)"""
    print("start myu3")
    myu3 = PhysQuant("100 mS/50 cm2")
    kwa = '''**{"num": (100.0, [], 1), "denom": (1.0, ['sec'], -1)}'''
    print("myu3", myu3)
    print("start myu4")
    myu4 = PhysQuant(kwa)
    print("myu4", myu4)
    print("start myu5")
    myu5 = PhysQuant(**{"num": (200.0, [], 1), "denom": (1.0, ['sec'], -1)})
    print("myu5", myu5)
    print("start myu6")
    myu6 = PhysQuant(num="300 pA")
    print("myu6", myu6)
    print("start myu7")
    myu7 = PhysQuant(pA=1)
    print("myu7", myu7)
    print("start myu8")
    myu8 = pq(100.0)
    print("myu8", myu8)
    print("start myu9")
    myu9 = myu3 * myu4
    print("myu9", myu9)
    print("Finished myu9")

    a = myu3.remove_prefix("50", "pA")
    print(a)
    b, _ = (myu6.SI)
    print(b)
    _, SIunit = myu6.SI
    b = myu3.add_prefix(myu6.scalar, SIunit)
    print(b)
    c=myu3.parse_unit_string("sec-1.cm3.mV")
    print(c)
    r = pq("8.314 J/mol.K")
    r.freeze
    R = r
    print(R.unit_dict)
    T = pq("23 oC")
    RT = R * T
    print(RT)
    resistivity = pq("100 ohm.cm")
    myu4invert = myu4.inverted()
    print("myu4", myu4, "inverted", myu4invert)