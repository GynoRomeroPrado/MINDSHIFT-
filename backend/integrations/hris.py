"""
HRIS Integration Connectors
Integrates with major HRIS systems (BambooHR, Workday, ADP, Gusto, etc.)
"""
import aiohttp
import logging
from typing import Dict, List, Optional
from datetime import datetime
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class HRISConnector(ABC):
    """Base class for HRIS integrations"""

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with HRIS system"""
        pass

    @abstractmethod
    async def get_employees(self) -> List[Dict]:
        """Get all active employees"""
        pass

    @abstractmethod
    async def get_employee(self, employee_id: str) -> Optional[Dict]:
        """Get single employee by ID"""
        pass

    @abstractmethod
    async def get_departments(self) -> List[Dict]:
        """Get all departments/teams"""
        pass

    @abstractmethod
    async def sync_employee_data(self) -> Dict:
        """Sync employee data from HRIS"""
        pass


class BambooHRConnector(HRISConnector):
    """
    BambooHR Integration
    Docs: https://documentation.bamboohr.com/docs
    """

    def __init__(self, subdomain: str, api_key: str):
        self.subdomain = subdomain
        self.api_key = api_key
        self.base_url = f"https://api.bamboohr.com/api/gateway.php/{subdomain}/v1"
        self.session = None

    async def authenticate(self) -> bool:
        """Test authentication"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/employees/directory",
                    auth=aiohttp.BasicAuth(self.api_key, 'x')
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"BambooHR authentication failed: {e}")
            return False

    async def get_employees(self) -> List[Dict]:
        """Get all active employees from BambooHR"""
        try:
            async with aiohttp.ClientSession() as session:
                # Get employee directory
                async with session.get(
                    f"{self.base_url}/employees/directory",
                    auth=aiohttp.BasicAuth(self.api_key, 'x'),
                    headers={'Accept': 'application/json'}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        employees = []

                        for emp in data.get('employees', []):
                            employees.append({
                                'id': emp.get('id'),
                                'email': emp.get('workEmail'),
                                'first_name': emp.get('firstName'),
                                'last_name': emp.get('lastName'),
                                'job_title': emp.get('jobTitle'),
                                'department': emp.get('department'),
                                'hire_date': emp.get('hireDate'),
                                'status': 'active' if emp.get('status') == 'Active' else 'inactive',
                                'manager_id': emp.get('supervisorEId')
                            })

                        return employees
                    else:
                        logger.error(f"Failed to fetch employees: {response.status}")
                        return []

        except Exception as e:
            logger.error(f"Error fetching BambooHR employees: {e}")
            return []

    async def get_employee(self, employee_id: str) -> Optional[Dict]:
        """Get single employee details"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/employees/{employee_id}",
                    auth=aiohttp.BasicAuth(self.api_key, 'x'),
                    headers={'Accept': 'application/json'}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'id': data.get('id'),
                            'email': data.get('workEmail'),
                            'first_name': data.get('firstName'),
                            'last_name': data.get('lastName'),
                            'job_title': data.get('jobTitle'),
                            'department': data.get('department'),
                            'hire_date': data.get('hireDate'),
                            'manager_id': data.get('supervisorEId')
                        }
                    return None

        except Exception as e:
            logger.error(f"Error fetching employee {employee_id}: {e}")
            return None

    async def get_departments(self) -> List[Dict]:
        """Get all departments"""
        # BambooHR doesn't have a dedicated departments endpoint
        # Extract departments from employee list
        employees = await self.get_employees()
        departments = set()

        for emp in employees:
            if emp.get('department'):
                departments.add(emp['department'])

        return [{'name': dept} for dept in departments]

    async def sync_employee_data(self) -> Dict:
        """Sync all employee data"""
        employees = await self.get_employees()
        return {
            'employees_synced': len(employees),
            'employees': employees,
            'timestamp': datetime.now().isoformat()
        }


class WorkdayConnector(HRISConnector):
    """
    Workday Integration
    Docs: https://community.workday.com/sites/default/files/file-hosting/productionapi/index.html
    """

    def __init__(self, tenant: str, username: str, password: str):
        self.tenant = tenant
        self.username = username
        self.password = password
        self.base_url = f"https://wd2-impl-services1.workday.com/ccx/service/{tenant}"

    async def authenticate(self) -> bool:
        """Test Workday authentication"""
        # Workday uses SOAP/REST APIs with basic auth
        # This is a simplified implementation
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/Human_Resources/v1",
                    auth=aiohttp.BasicAuth(self.username, self.password)
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Workday authentication failed: {e}")
            return False

    async def get_employees(self) -> List[Dict]:
        """Get all employees from Workday"""
        # Workday requires SOAP/REST API calls
        # This is a simplified implementation
        logger.info("Workday get_employees - implement SOAP API call")
        return []

    async def get_employee(self, employee_id: str) -> Optional[Dict]:
        """Get single employee from Workday"""
        logger.info(f"Workday get_employee {employee_id} - implement SOAP API call")
        return None

    async def get_departments(self) -> List[Dict]:
        """Get departments from Workday"""
        logger.info("Workday get_departments - implement SOAP API call")
        return []

    async def sync_employee_data(self) -> Dict:
        """Sync employee data from Workday"""
        return {
            'employees_synced': 0,
            'employees': [],
            'timestamp': datetime.now().isoformat(),
            'note': 'Workday integration requires SOAP API implementation'
        }


class GustoConnector(HRISConnector):
    """
    Gusto Integration
    Docs: https://docs.gusto.com/
    """

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://api.gusto.com/v1"

    async def authenticate(self) -> bool:
        """Test Gusto authentication"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/me",
                    headers={'Authorization': f'Bearer {self.api_token}'}
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Gusto authentication failed: {e}")
            return False

    async def get_employees(self) -> List[Dict]:
        """Get all employees from Gusto"""
        try:
            async with aiohttp.ClientSession() as session:
                # First get company ID
                async with session.get(
                    f"{self.base_url}/me",
                    headers={'Authorization': f'Bearer {self.api_token}'}
                ) as response:
                    if response.status != 200:
                        return []

                    me_data = await response.json()
                    company_id = me_data.get('companies', [{}])[0].get('id')

                # Get employees
                async with session.get(
                    f"{self.base_url}/companies/{company_id}/employees",
                    headers={'Authorization': f'Bearer {self.api_token}'}
                ) as response:
                    if response.status == 200:
                        employees_data = await response.json()
                        employees = []

                        for emp in employees_data:
                            employees.append({
                                'id': emp.get('id'),
                                'email': emp.get('email'),
                                'first_name': emp.get('first_name'),
                                'last_name': emp.get('last_name'),
                                'job_title': emp.get('jobs', [{}])[0].get('title'),
                                'department': emp.get('department'),
                                'hire_date': emp.get('hire_date'),
                                'status': 'active' if emp.get('terminated') is None else 'inactive',
                                'manager_id': emp.get('manager_id')
                            })

                        return employees

            return []

        except Exception as e:
            logger.error(f"Error fetching Gusto employees: {e}")
            return []

    async def get_employee(self, employee_id: str) -> Optional[Dict]:
        """Get single employee from Gusto"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/employees/{employee_id}",
                    headers={'Authorization': f'Bearer {self.api_token}'}
                ) as response:
                    if response.status == 200:
                        emp = await response.json()
                        return {
                            'id': emp.get('id'),
                            'email': emp.get('email'),
                            'first_name': emp.get('first_name'),
                            'last_name': emp.get('last_name'),
                            'job_title': emp.get('jobs', [{}])[0].get('title'),
                            'department': emp.get('department'),
                            'hire_date': emp.get('hire_date')
                        }
            return None

        except Exception as e:
            logger.error(f"Error fetching employee {employee_id}: {e}")
            return None

    async def get_departments(self) -> List[Dict]:
        """Get departments from Gusto"""
        employees = await self.get_employees()
        departments = set()

        for emp in employees:
            if emp.get('department'):
                departments.add(emp['department'])

        return [{'name': dept} for dept in departments]

    async def sync_employee_data(self) -> Dict:
        """Sync employee data from Gusto"""
        employees = await self.get_employees()
        return {
            'employees_synced': len(employees),
            'employees': employees,
            'timestamp': datetime.now().isoformat()
        }


class HRISIntegrationService:
    """
    Main HRIS Integration Service
    Manages connections to multiple HRIS systems
    """

    def __init__(self):
        self.connectors: Dict[str, HRISConnector] = {}

    def add_connector(self, name: str, connector: HRISConnector):
        """Add an HRIS connector"""
        self.connectors[name] = connector
        logger.info(f"Added HRIS connector: {name}")

    async def sync_from_hris(self, hris_name: str) -> Dict:
        """
        Sync employee data from specified HRIS

        Args:
            hris_name: Name of HRIS system (bamboohr, workday, gusto, etc.)

        Returns:
            Sync results dictionary
        """
        connector = self.connectors.get(hris_name)
        if not connector:
            return {
                'success': False,
                'error': f'HRIS connector not found: {hris_name}'
            }

        # Test authentication
        auth_success = await connector.authenticate()
        if not auth_success:
            return {
                'success': False,
                'error': 'Authentication failed'
            }

        # Sync data
        result = await connector.sync_employee_data()
        result['success'] = True
        result['hris_system'] = hris_name

        return result

    async def get_all_employees(self, hris_name: str) -> List[Dict]:
        """Get all employees from HRIS"""
        connector = self.connectors.get(hris_name)
        if not connector:
            logger.error(f"HRIS connector not found: {hris_name}")
            return []

        return await connector.get_employees()

    async def update_organization_from_hris(self, organization_id: int, hris_name: str, db):
        """
        Update MindShift organization with data from HRIS

        Args:
            organization_id: Organization ID in MindShift
            hris_name: HRIS system name
            db: Database session
        """
        from models import User, Department, Organization
        from auth import get_password_hash

        # Get employees from HRIS
        employees = await self.get_all_employees(hris_name)

        if not employees:
            logger.warning(f"No employees found in {hris_name}")
            return {
                'success': False,
                'error': 'No employees found'
            }

        # Get organization
        organization = db.query(Organization).filter(
            Organization.id == organization_id
        ).first()

        if not organization:
            return {
                'success': False,
                'error': 'Organization not found'
            }

        # Create/update departments
        department_map = {}
        departments = set(emp['department'] for emp in employees if emp.get('department'))

        for dept_name in departments:
            dept = db.query(Department).filter(
                Department.organization_id == organization_id,
                Department.name == dept_name
            ).first()

            if not dept:
                dept = Department(
                    organization_id=organization_id,
                    name=dept_name
                )
                db.add(dept)
                db.flush()

            department_map[dept_name] = dept.id

        # Create/update users
        users_created = 0
        users_updated = 0

        for emp_data in employees:
            if not emp_data.get('email'):
                continue

            # Check if user exists
            user = db.query(User).filter(
                User.email == emp_data['email']
            ).first()

            department_id = department_map.get(emp_data.get('department'))

            if not user:
                # Create new user
                user = User(
                    organization_id=organization_id,
                    department_id=department_id,
                    email=emp_data['email'],
                    hashed_password=get_password_hash('ChangeMe123!'),  # Temp password
                    full_name=f"{emp_data.get('first_name', '')} {emp_data.get('last_name', '')}".strip(),
                    job_title=emp_data.get('job_title'),
                    hire_date=datetime.fromisoformat(emp_data['hire_date']) if emp_data.get('hire_date') else None,
                    is_active=emp_data.get('status') == 'active'
                )
                db.add(user)
                users_created += 1
            else:
                # Update existing user
                user.full_name = f"{emp_data.get('first_name', '')} {emp_data.get('last_name', '')}".strip()
                user.job_title = emp_data.get('job_title')
                user.department_id = department_id
                user.is_active = emp_data.get('status') == 'active'
                users_updated += 1

        db.commit()

        logger.info(f"HRIS sync complete: {users_created} created, {users_updated} updated")

        return {
            'success': True,
            'users_created': users_created,
            'users_updated': users_updated,
            'departments_created': len(departments)
        }


# Global integration service
hris_service = HRISIntegrationService()
