CREATE DATABASE IF NOT EXISTS landlorddb;
USE landlorddb;
############CREATES################
CREATE TABLE Houses(
Address varchar(20) PRIMARY KEY,
Apartment_count numeric(3,0),
Property_value numeric(10,2)
);

CREATE TABLE Apartments(
Apartment_ID numeric(3,0) PRIMARY KEY,
address varchar(20),
number numeric(3,0),
size numeric(3,0),
room_count numeric(3,0),
has_parking_lot varchar(3),
FOREIGN KEY (address) REFERENCES Houses(Address)
);

CREATE TABLE Tennents(
Tennent_ID numeric(3,0) PRIMARY KEY,
surname varchar(20),
name varchar(20),
warning_count numeric(3,0)
);

CREATE TABLE Contractors(
Contract_ID numeric(3,0) PRIMARY KEY,
con_surname varchar(20),
con_name varchar(20),
address varchar(20),
profession varchar(40)
);

CREATE TABLE Leases(
Lease_ID numeric(4,0) PRIMARY KEY,
Apartment_ID numeric(3,0),
tennent_ID numeric(3,0),
Validation_date date,
rent numeric(6,2),
utilities numeric(5,2),
termination date,
FOREIGN KEY (Tennent_ID) REFERENCES Tennents(Tennent_ID),
FOREIGN KEY (Apartment_ID) REFERENCES Apartments(Apartment_ID)
);

CREATE TABLE Warnings(
Warning_ID numeric(3,0) PRIMARY KEY,
lease_ID numeric(4,0),
date date,
fine_amount numeric(8,2),
is_paid varchar(3),
FOREIGN KEY (lease_ID) REFERENCES Leases(lease_ID)
);

CREATE TABLE Repairs(
repair_ID numeric(3,0),
apartment_ID numeric(3,0),
Contract_ID numeric(3,0),
issue_description varchar(200),
repair_cost numeric(8,2),
completion_status varchar(3),
FOREIGN KEY (Apartment_ID) REFERENCES Apartments(Apartment_ID),
FOREIGN KEY (Contract_ID) REFERENCES Contractors(Contract_ID)
);


###################INSERTS#############
INSERT into Houses
(Address, Apartment_count, Property_value)
VALUES
('123 Main Street', 4, 450000),
('456 Oak Avenue', 3, 350000),
('789 Pine Road', 5, 600000),
('321 Maple Drive', 2, 275000),
('654 Cedar Lane', 4, 500000);

INSERT into Apartments
(Apartment_ID, address, number, size, room_count, has_parking_lot)
VALUES
(1, '123 Main Street', 101, 92, 3, 'Yes'),
(2, '123 Main Street', 102, 63, 2, 'No'),
(3, '456 Oak Avenue', 201, 110, 4, 'Yes'),
(4, '789 Pine Road', 301, 65, 2, 'No'),
(5, '321 Maple Drive', 401, 120, 4, 'Yes'),
(6, '654 Cedar Lane', 501, 85, 3, 'Yes');


INSERT into Tennents
(Tennent_ID, surname, name, warning_count)
VALUES
(101, 'Anderson', 'Sarah', 0),
(102, 'Taylor', 'James', 1),
(103, 'Thomas', 'Emily', 2),
(104, 'Jackson', 'Daniel', 0),
(105, 'White', 'Jessica', 1);

INSERT into Contractors
(Contract_ID, con_surname, con_name, address, profession)
VALUES
(1, 'Smith', 'John', '123 Main Street', 'Plumber'),
(2, 'Johnson', 'Michael', '45 Oak Street', 'Electrician'),
(3, 'Williams', 'David', '78 Pine Street', 'Carpenter'),
(4, 'Brown', 'James', '90 Maple Street', 'Painter'),
(5, 'Davis', 'Robert', '12 Cedar Street', 'General Contractor');


INSERT into Leases
(Lease_ID, Apartment_ID, tennent_ID, Validation_date,
rent, utilities, termination)
VALUES
(1001, 1, 101, '2025-01-01', 1200, 150, '2026-01-01'),
(1002, 2, 102, '2025-03-01', 950, 100, '2026-03-01'),
(1003, 3, 103, '2025-06-01', 1400, 175, '2026-06-01'),
(1004, 4, 104, '2025-09-01', 850, 125, '2026-09-01'),
(1005, 5, 105, '2025-12-01', 1600, 200, '2026-12-01');

INSERT into Warnings
(Warning_ID, lease_ID, date, fine_amount, is_paid)
VALUES
(1, 1002, '2025-04-15', 50, 'Yes'),
(2, 1003, '2025-07-20', 100, 'No'),
(3, 1003, '2025-08-10', 75, 'Yes'),
(4, 1005, '2026-01-05', 50, 'No');

INSERT into Repairs
(repair_ID, apartment_ID, Contract_ID, issue_description,
repair_cost, completion_status)
VALUES
(1, 1, 1, 'Leaking kitchen sink', 150, 'Yes'),
(2, 2, 2, 'Faulty electrical outlet', 200, 'Yes'),
(3, 3, 3, 'Broken bedroom door', 175, 'Yes'),
(4, 4, 4, 'Bathroom needs repairing', 300, 'No'),
(5, 5, 5, 'Damaged flooring', 500, 'No'),
(6, 6, 1, 'Leaking bathroom faucet', 100, 'Yes');

######QUERIES#########
# Query 1: Get value of whole property 
delimiter //
create procedure get_total_value()
    reads sql data
    begin
        select sum(Property_value) as total  
        from Houses;
    end //
delimiter ;

#Query 2 and 3: Filtering free apartments 
create view free_apartments as 
    select *
    from Apartments 
    where Apartment_ID not in (
        select Apartment_ID
        from Leases
    );
delimiter //
create procedure get_apartments(in squarmeters numeric(3,0), in rooms numeric(3,0), parking varchar(3))
reads sql data 
begin
    select *
    from free_apartments
    where (size < squarmeters) or (room_count < rooms) or (has_parking_lot = parking);
end // 
delimiter ; 

#Query 4
create view critical_leases as 
    select *
    from Leases 
    where Lease_ID in (
        select Lease_ID
        from Warnings
        where is_paid = 'No'
    );
delimiter //
create procedure get_critical_lease()
reads sql data 
begin   
select *
from critical_leases;
end // 
delimiter ; 

#Query 5
delimiter //
create procedure get_less_jobs()
reads sql data 
begin 
select *
from Contractors
where Contract_ID in (
    select Contract_ID
    from Repairs
    group by Contract_ID
    having count(*) = (
        select min(jobs)
        from (
        select count(*) as jobs
        from Repairs
        group by Contract_ID) as all_jobs));
end //
delimiter ;

#Query 6
delimiter //
create procedure show_broken_apartments()
reads sql data 
begin 
select Apartment_ID, address, number, repair_ID, Contract_ID, issue_description, repair_cost 
from Apartments
natural JOIN Repairs
where completion_status = 'No';
end //
delimiter ; 

#Query 7
delimiter //
create procedure prio_repairs()
reads sql data 
begin 
select repair_ID, apartment_ID, Contract_ID, issue_description,
repair_cost, completion_status 
from Tennents
natural join Leases
natural join Repairs
where warning_count = 0
and completion_status = 'No';
end //
delimiter ; 

#Query 8
delimiter //
create procedure new_warning_letter()
reads sql data 
begin 
select Tennents.Tennent_ID, name, surname, rent, fine_amount, address
from Tennents join Leases on Tennents.Tennent_ID = Leases.Tennent_ID
join Warnings on Leases.Lease_ID = Warnings.lease_ID 
join Apartments on Apartments.Apartment_ID = Leases.Apartment_ID
where Warnings.is_paid = 'No';
end //
delimiter ;

#Query 9: check the avg of all warnings and repairs per house
delimiter //
create procedure get_critical_houses()
reads sql data 
begin 
select Apartments.address, 
(count(Distinct Warning_ID) / Apartment_count) as avg_warnings,
(count(Distinct Repair_ID) / Apartment_count) as avg_repairs
from Houses
Left Join Apartments
on Houses.address = Apartments.address
left join Leases
on Apartments.Apartment_ID = Leases.Apartment_ID
left join Warnings
on Leases.Lease_ID =Warnings.Lease_ID
left join Repairs
on Apartments.Apartment_ID = Repairs.Apartment_ID
group by Houses.address, Houses.Apartment_count;
end //
delimiter ; 

#Query 10: 
delimiter //
create procedure check_house(in adr varchar(20))
reads sql data 
begin 
select Address, monthly_rent, repair_cost,
        coalesce(monthly_rent, 0) - coalesce(repair_cost, 0) as saldo
from(
select Houses.Address,
    (select SUM(rent)
     from Leases
     join Apartments using (Apartment_ID)
     where Apartments.address = Houses.Address) AS monthly_rent,

    (select SUM(repair_cost)
     from Repairs
     join Apartments using (Apartment_ID)
     where Apartments.address = Houses.Address) AS repair_cost
from Houses
where Houses.Address like concat('%',adr,'%')) as house;
end //
delimiter ; 


#Trigger 1: Automatically increase a tennents warning coount whenever a new warning is inserted
delimiter //
create trigger update_warning_count
after insert on Warnings
for each row
begin 
update Tennents
set warning_count = warning_count + 1
where Tennent_ID = (select Tennent_ID from Leases where Lease_ID = new.lease_ID);
end //
delimiter ; 