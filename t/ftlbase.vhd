library ieee;
use ieee.std_logic_1164.all;

package ftlbase is

constant ZERO_std_ulogic : std_ulogic := '0';
constant UNDEF_std_ulogic : std_ulogic := 'U';

function to_bool(x: std_ulogic) return boolean;
function to_stdulogic(x: boolean) return std_ulogic;

function zero_std_logic_vector(hi: integer; lo: integer) return std_logic_vector;
function undef_std_logic_vector(hi: integer; lo: integer) return std_logic_vector;

end;

package body ftlbase is

function to_bool(x: std_ulogic) return boolean is
begin
    return (x = '1');
end function to_bool;

function to_stdulogic(x: boolean) return std_ulogic is
begin
    if x then
        return '1';
    else
        return '0';
    end if;
end function;

function zero_std_logic_vector(hi: integer; lo: integer) return std_logic_vector is
variable v : std_logic_vector(hi downto lo) := (others => '0');
begin
    return v;
end function zero_std_logic_vector;

function undef_std_logic_vector(hi: integer; lo: integer) return std_logic_vector is
variable v : std_logic_vector(hi downto lo) := (others => 'U');
begin
    return v;
end function undef_std_logic_vector;

end;
