# -*- coding: utf-8 -*-
"""
Created on Mon Sep 14 22:52:44 2015

@author: ppfaff
Program to run unittests on PhysQuant code, currently residing in the
PQ_math_reorg file.  
"""

from PQ_math_reorg import *
from unittest import TestCase, main

class PhysQuantTestCase(TestCase):
    """these tests check the ability of various inputs to create PhysQuant
    objects"""
    def test_PhysQuant_string(self):
        """Test a string with both units and a math operation"""
        self.assertIsInstance(PhysQuant("100 mS/50 cm2"), PhysQuant)
    def test_PhysQuant_dictstr(self):
        """Test a kwarg type string passed in as an *arg"""
        kwa = '''**{"num": (100.0, [], 1), "denom": (1.0, ['sec'], -1)}'''
        self.assertIsInstance(PhysQuant(kwa), PhysQuant)
    def test_PhysQuant_dict_kwargs(self):
        """Test a dict passed as a **kwarg"""
        self.assertIsInstance(PhysQuant(**{"num": (200.0, [], 1), "denom": (1.0, ['sec'], -1)}), PhysQuant)
    def test_PhysQuant_num_kwarg(self):    
        """Test a keyword defining num or denom equal to a value, unit string"""
        self.assertIsInstance(PhysQuant(num="300 pA"), PhysQuant)
        self.assertIsInstance(PhysQuant(denom="100 msec"), PhysQuant)
    def test_PhysQuant_float(self):
        """Test a float input"""
        self.assertIsInstance(PhysQuant(1.4e-3), PhysQuant)
    def test_PhysQuant_unit_kwarg(self):
        """Test a unit = float input"""
        self.assertIsInstance(PhysQuant(pA=1.56), PhysQuant)
    def test_PhysQuant_pq_mult(self):
        """ This is a test of multiplication between two PhysQuant objects"""
        self.assertIsInstance(PhysQuant("100 mS/50 cm2")*PhysQuant(num="300 pA"), PhysQuant)
    def test_PhysQuant_pq_mult_float(self):
        """These are tests of multiplication with a float before or after"""
        self.assertIsInstance(PhysQuant("100 mS/50 cm2") * 1.45e-4, PhysQuant)
        self.assertIsInstance(1.45e-4 * PhysQuant("100 mS/50 cm2"), PhysQuant)
    def test_PhysQuant_pq_mult_float(self):
        """This tests if a defined parameter can be froze and melted between
        a mutable list and tuple and whether that property can be passed on"""
        r = pq("8.314 J/mol.K")
        self.assertIsInstance(r._unit_dict["num"][1], list)
        r.freeze()
        self.assertIsInstance(r._unit_dict["num"][1], tuple)
        R = r
        print(R.unit_dict)
        self.assertIsInstance(R.unit_dict, dict)
        self.assertIsInstance(R._unit_dict["num"][1], tuple)
    def test_PhysQuant_pq_temp(self):
        """ This tests the handling of Temperature conversions to Kelvins"""
        T = pq("23 oC")
        self.assertIsInstance(T, PhysQuant)
        self.assertAlmostEqual(T.scalar, 273.15+23)
        Tf = pq("32 oF")
        self.assertIsInstance(Tf, PhysQuant)
        self.assertAlmostEqual(Tf.scalar, 273.15)

    def test_PhysQuant_invert_ohm_cm(self):
        """ This tests the conversions betweeen Siemens and ohms when inverted"""
        resist = pq("100 ohm")
        conduct = resistivity.inverted()
        self.assertEqual(conduct.SI, "S")
    def test_PhysQuant_invert_ohm_cm(self):
        """ This tests for the conversion between Siemens and ohms when
        inverted as part of a more complex unit product"""
        resistivity = pq("100 ohm.cm")
        gps = resistivity.inverted()
        print("gps_unitDict: ", gps._unit_dict)
        self.assertEqual(gps.SI, (1.0, "S/m"))
    def test_PhysQuant_reduce_all(self):
        """ Tests the full reduction of units"""
        print("*****Begin test Reduce All*****")
        a = pq("1e6 ohm")
        b = pq("1e-6 F")
        c = a * b
        print("c dict", c.unit_dict)
        c.reduce_all()
        self.assertEqual(c.SI, (1.0, "sec"))
      
        
if __name__ == "__main__":
    main()

""" print(MyQuant.prefixed)
    
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
    b = (myu6.scalar, myu6.SI)
    print(b)
    b = myu3.add_prefix(myu6.scalar, myu6.SI)
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
    print("myu4", myu4, "inverted", myu4invert)"""