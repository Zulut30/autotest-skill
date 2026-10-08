"""Native actions on an explicit isolated Appium device with bounded transport."""

import json
import os
from pathlib import Path
import httpx
from ..artifacts import safe_file,write_json
from ..errors import Blocked
from ..policy import require_url
from urllib3.exceptions import ReadTimeoutError,ConnectTimeoutError


def run(check,context):
    from appium import webdriver
    from appium.options.android import UiAutomator2Options
    from appium.webdriver.client_config import AppiumClientConfig
    from appium.webdriver.common.appiumby import AppiumBy
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.common.exceptions import TimeoutException,NoSuchElementException,WebDriverException
    spec=check.spec
    require_url(context.config,spec.server_url)
    context.consume('requests')
    try:
        health=httpx.get(spec.server_url+'/status',timeout=min(5,context.remaining()))
        if health.status_code!=200 or not health.json().get('value',{}).get('ready'):
            raise Blocked('Appium server is not ready')
    except (httpx.HTTPError,ValueError) as exc:
        raise Blocked('Appium server is unavailable') from exc
    capabilities={'platformName':'Android','appium:automationName':'UiAutomator2','appium:udid':spec.udid,
        'appium:deviceName':spec.device_name,'appium:appPackage':spec.package,'appium:appActivity':spec.activity,
        'appium:noReset':not spec.reset,'appium:newCommandTimeout':max(10,int(spec.timeout)),
        'appium:androidInstallTimeout':int(min(spec.timeout,context.remaining())*1000),
        'appium:adbExecTimeout':int(min(spec.timeout,context.remaining())*1000),
        'appium:uiautomator2ServerLaunchTimeout':int(min(spec.timeout,context.remaining())*1000),
        'appium:disableWindowAnimation':True,'appium:settings[waitForIdleTimeout]':0,
        'appium:settings[waitForSelectorTimeout]':0,'appium:skipLogcatCapture':True}
    if spec.reuse_runtime:
        capabilities['appium:skipDeviceInitialization']=True
        capabilities['appium:skipServerInstallation']=True
    if spec.apk:
        root=Path(context.root).resolve();apk=(root/spec.apk).resolve()
        if root not in apk.parents or not apk.is_file():
            raise Blocked('Configured APK is missing or outside the project')
        capabilities['appium:app']=str(apk)
    client=AppiumClientConfig(remote_server_addr=spec.server_url,timeout=min(spec.timeout,context.remaining()))
    driver=None
    actual={'device':spec.udid,'request_budget_scope':'Explicit Appium operations; downstream protocol frames are not counted.'}
    evidence=[]
    status,reason='passed',''
    def call(function,*args,**kwargs):
        context.consume('requests')
        client.timeout=min(spec.timeout,context.remaining())
        return function(*args,**kwargs)
    def locate(action):
        if action.accessibility_id: kind,value=AppiumBy.ACCESSIBILITY_ID,action.accessibility_id
        elif action.resource_id: kind,value=AppiumBy.ID,action.resource_id
        elif action.text: kind,value=AppiumBy.ANDROID_UIAUTOMATOR,'new UiSelector().text('+json.dumps(action.text)+')'
        else:raise ValueError('Native action requires a semantic locator')
        def found(_):
            elements=call(driver.find_elements,kind,value)
            if len(elements)>1:raise Blocked('Configured native locator is ambiguous')
            return elements[0] if elements and call(elements[0].is_displayed) else False
        return WebDriverWait(driver,min(spec.timeout,context.remaining()),poll_frequency=.25).until(found)
    try:
        context.consume('actions')
        driver=call(webdriver.Remote,spec.server_url,options=UiAutomator2Options().load_capabilities(capabilities),client_config=client)
        actual['platform_version']=driver.capabilities.get('platformVersion')
        for index,action in enumerate(spec.actions):
            context.consume('actions');actual['last_action']=index
            value=context.redactor.binding(action.value_env) if action.value_env else action.value
            if action.action=='back':call(driver.back)
            elif action.action=='background':call(driver.background_app,2)
            elif action.action=='restart':
                call(driver.terminate_app,spec.package);call(driver.activate_app,spec.package)
            elif action.action=='set_network':
                if action.enabled is None:raise ValueError('Connectivity action requires enabled')
                call(driver.execute_script,'mobile: setConnectivity',{'wifi':action.enabled,'data':action.enabled,'airplaneMode':not action.enabled})
            elif action.action=='hide_keyboard':
                if call(driver.is_keyboard_shown):call(driver.hide_keyboard)
            elif action.action=='scroll_to':
                selector='new UiSelector().description('+json.dumps(action.accessibility_id)+')' if action.accessibility_id else ('new UiSelector().text('+json.dumps(action.text)+')' if action.text else 'new UiSelector().resourceId('+json.dumps(action.resource_id)+')')
                call(driver.find_element,AppiumBy.ANDROID_UIAUTOMATOR,'new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView('+selector+')')
            elif action.action=='screenshot':pass
            else:
                element=locate(action)
                if action.action=='click':call(element.click)
                elif action.action=='fill':call(element.clear);call(element.send_keys,value or '')
                elif action.action=='expect_text' and value is not None:
                    observed=call(lambda:element.text)
                    if observed!=value:raise AssertionError('Native text differs from the oracle')
        actual['package']=call(lambda:driver.current_package)
        actual['viewport']=call(driver.get_window_size)
    except Blocked as exc:
        status,reason='blocked',context.redactor.text(str(exc))
    except (AssertionError,TimeoutException,NoSuchElementException) as exc:
        status,reason='failed',f'Native UI oracle was not satisfied ({type(exc).__name__})'
    except (ReadTimeoutError,ConnectTimeoutError) as exc:
        status,reason="blocked","Appium transport exceeded its bounded timeout"
    except WebDriverException as exc:
        status,reason='blocked' if driver is None else 'error',f'Native runner operation did not complete ({type(exc).__name__})'
    finally:
        if driver is not None:
            client.timeout=5
            image=f'{check.id}.png'
            try:
                if any(a.value_env for a in spec.actions):
                    raise Blocked('Screenshot withheld because secret-bound actions were used')
                driver.save_screenshot(str(safe_file(context.folder,image)))
                os.chmod(safe_file(context.folder,image),0o600);evidence.append(image)
            except Exception:actual['screenshot_unavailable']=True
            try:driver.quit()
            except Exception:actual['session_cleanup_error']=True
    artifact=f'{check.id}.android.json'
    write_json(context.folder,artifact,actual,context.redactor);evidence.append(artifact)
    return context.result(check,status,actual=actual,reason=reason,evidence=evidence)
