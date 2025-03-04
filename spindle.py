import os # noqa
import sys # noqa
import argparse
import random
import time
import copy
import pdb # noqa
import shutil
import math
import re
# from datetime import datetime

from DrissionPage import ChromiumOptions
from DrissionPage import ChromiumPage
from DrissionPage._elements.none_element import NoneElement
# from DrissionPage.common import Keys
# from DrissionPage import Chromium
# from DrissionPage.common import Actions
# from DrissionPage.common import Settings

from fun_utils import ding_msg
from fun_utils import get_date
from fun_utils import load_file
from fun_utils import save2file
from fun_utils import format_ts
# from fun_utils import time_difference
from fun_utils import extract_numbers

from conf import DEF_LOCAL_PORT
from conf import DEF_INCOGNITO
from conf import DEF_USE_HEADLESS
from conf import DEF_DEBUG
from conf import DEF_PATH_USER_DATA
from conf import DEF_NUM_TRY
from conf import DEF_DING_TOKEN
from conf import DEF_PATH_BROWSER
from conf import DEF_PATH_DATA_STATUS
from conf import DEF_HEADER_STATUS
from conf import DEF_OKX_EXTENSION_PATH
from conf import EXTENSION_ID_OKX
from conf import DEF_PWD
from conf import DEF_FEE_MAX_BASE
from conf import DEF_FEE_PRIORITY

from conf import DEF_MINT_USDC_MIN
from conf import DEF_MINT_USDC_MAX
from conf import DEF_MINT_WBTC_MIN
from conf import DEF_MINT_WBTC_MAX

from conf import DEF_PATH_DATA_PURSE
from conf import DEF_HEADER_PURSE

from conf import TZ_OFFSET
from conf import DEL_PROFILE_DIR

from conf import logger

"""
2024.12.23
https://dev.app.spindlefinance.xyz/mint
"""

# Wallet balance
DEF_INSUFFICIENT = -1
DEF_SUCCESS = 0
DEF_FAIL = 1


class SpindleTask():
    def __init__(self) -> None:
        self.args = None
        self.page = None
        self.s_today = get_date(is_utc=True)
        self.file_proxy = None

        self.n_points_spin = -1
        self.n_points = -1
        self.n_referrals = -1
        self.n_completed = -1

        # 是否有更新
        self.is_update = False

        # 账号执行情况
        self.dic_status = {}

        self.dic_purse = {}

        self.purse_load()

    def set_args(self, args):
        self.args = args
        self.is_update = False

        self.n_points_spin = -1
        self.n_points = -1
        self.n_referrals = -1
        self.n_completed = -1

    def __del__(self):
        self.status_save()

    def purse_load(self):
        self.file_purse = f'{DEF_PATH_DATA_PURSE}/purse.csv'
        self.dic_purse = load_file(
            file_in=self.file_purse,
            idx_key=0,
            header=DEF_HEADER_PURSE
        )

    def status_load(self):
        self.file_status = f'{DEF_PATH_DATA_STATUS}/status.csv'
        self.dic_status = load_file(
            file_in=self.file_status,
            idx_key=0,
            header=DEF_HEADER_STATUS
        )

    def status_save(self):
        self.file_status = f'{DEF_PATH_DATA_STATUS}/status.csv'
        save2file(
            file_ot=self.file_status,
            dic_status=self.dic_status,
            idx_key=0,
            header=DEF_HEADER_STATUS
        )

    def close(self):
        # 在有头浏览器模式 Debug 时，不退出浏览器，用于调试
        if DEF_USE_HEADLESS is False and DEF_DEBUG:
            pass
        else:
            if self.page:
                try:
                    self.page.quit()
                except Exception as e:
                    logger.info(f'[Close] Error: {e}')

    def initChrome(self, s_profile):
        """
        s_profile: 浏览器数据用户目录名称
        """
        # Settings.singleton_tab_obj = True

        profile_path = s_profile

        # 是否设置无痕模式
        if DEF_INCOGNITO:
            co = ChromiumOptions().incognito(True)
        else:
            co = ChromiumOptions()

        # 设置本地启动端口
        co.set_local_port(port=DEF_LOCAL_PORT)
        if len(DEF_PATH_BROWSER) > 0:
            co.set_paths(browser_path=DEF_PATH_BROWSER)
        # co.set_paths(browser_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome') # noqa

        co.set_argument('--accept-lang', 'en-US')  # 设置语言为英语（美国）
        co.set_argument('--lang', 'en-US')

        # 阻止“自动保存密码”的提示气泡
        co.set_pref('credentials_enable_service', False)

        # 阻止“要恢复页面吗？Chrome未正确关闭”的提示气泡
        co.set_argument('--hide-crash-restore-bubble')

        # 关闭沙盒模式
        # co.set_argument('--no-sandbox')

        # popups支持的取值
        # 0：允许所有弹窗
        # 1：只允许由用户操作触发的弹窗
        # 2：禁止所有弹窗
        # co.set_pref(arg='profile.default_content_settings.popups', value='0')

        co.set_user_data_path(path=DEF_PATH_USER_DATA)
        co.set_user(user=profile_path)

        # 获取当前工作目录
        current_directory = os.getcwd()

        # 检查目录是否存在
        if os.path.exists(os.path.join(current_directory, DEF_OKX_EXTENSION_PATH)): # noqa
            logger.info(f'okx plugin path: {DEF_OKX_EXTENSION_PATH}')
            co.add_extension(DEF_OKX_EXTENSION_PATH)
        else:
            print("okx plugin directory is not exist. Exit!")
            sys.exit(1)

        # https://drissionpage.cn/ChromiumPage/browser_opt
        co.headless(DEF_USE_HEADLESS)
        co.set_user_agent(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36') # noqa

        try:
            self.page = ChromiumPage(co)
        except Exception as e:
            logger.info(f'Error: {e}')
        finally:
            pass

        self.page.wait.load_start()
        # self.page.wait(2)

        # tab_new = self.page.new_tab()
        # self.page.close_tabs(tab_new, others=True)

        # 浏览器启动时有 okx 弹窗，关掉
        # self.check_start_tabs()

    def logit(self, func_name=None, s_info=None):
        s_text = f'{self.args.s_profile}'
        if func_name:
            s_text += f' [{func_name}]'
        if s_info:
            s_text += f' {s_info}'
        logger.info(s_text)

    def close_popup_tabs(self, s_keep='OKX Web3'):
        # 关闭 OKX 弹窗
        if len(self.page.tab_ids) > 1:
            self.logit('close_popup_tabs', None)
            n_width_max = -1
            for tab_id in self.page.tab_ids:
                n_width_tab = self.page.get_tab(tab_id).rect.size[0]
                if n_width_max < n_width_tab:
                    n_width_max = n_width_tab

            tab_ids = self.page.tab_ids
            n_tabs = len(tab_ids)
            for i in range(n_tabs-1, -1, -1):
                tab_id = tab_ids[i]
                n_width_tab = self.page.get_tab(tab_id).rect.size[0]
                if n_width_tab < n_width_max:
                    s_title = self.page.get_tab(tab_id).title
                    self.logit(None, f'Close tab:{s_title} width={n_width_tab} < {n_width_max}') # noqa
                    self.page.get_tab(tab_id).close()
                    return True
        return False

    def is_exist(self, s_title, s_find, match_type):
        b_ret = False
        if match_type == 'fuzzy':
            if s_title.find(s_find) >= 0:
                b_ret = True
        else:
            if s_title == s_find:
                b_ret = True

        return b_ret

    def check_start_tabs(self, s_keep='新标签页', match_type='fuzzy'):
        """
        关闭多余的标签页
        match_type
            precise 精确匹配
            fuzzy 模糊匹配
        """
        if self.page.tabs_count > 1:
            self.logit('check_start_tabs', None)
            tab_ids = self.page.tab_ids
            n_tabs = len(tab_ids)
            for i in range(n_tabs-1, -1, -1):
                tab_id = tab_ids[i]
                s_title = self.page.get_tab(tab_id).title
                # print(f's_title={s_title}')
                if self.is_exist(s_title, s_keep, match_type):
                    continue
                if len(self.page.tab_ids) == 1:
                    break
                self.logit(None, f'Close tab:{s_title}')
                self.page.get_tab(tab_id).close()
            self.logit(None, f'Keeped tab: {self.page.title}')
            return True
        return False

    def okx_secure_wallet(self):
        # Secure your wallet
        ele_info = self.page.ele('Secure your wallet')
        if not isinstance(ele_info, NoneElement):
            self.logit('okx_secure_wallet', 'Secure your wallet')
            ele_btn = self.page.ele('Password', timeout=2)
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.page.wait(1)
                self.logit('okx_secure_wallet', 'Select Password')

                # Next
                ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.page.wait(1)
                    self.logit('okx_secure_wallet', 'Click Next')
                    return True
        return False

    def okx_set_pwd(self):
        # Set password
        ele_info = self.page.ele('Set password', timeout=2)
        if not isinstance(ele_info, NoneElement):
            self.logit('okx_set_pwd', 'Set Password')
            ele_input = self.page.ele('@@tag()=input@@data-testid=okd-input@@placeholder:Enter', timeout=2) # noqa
            if not isinstance(ele_input, NoneElement):
                self.logit('okx_set_pwd', 'Input Password')
                self.page.actions.move_to(ele_input).click().type(DEF_PWD)
            self.page.wait(1)
            ele_input = self.page.ele('@@tag()=input@@data-testid=okd-input@@placeholder:Re-enter', timeout=2) # noqa
            if not isinstance(ele_input, NoneElement):
                self.page.actions.move_to(ele_input).click().type(DEF_PWD)
                self.logit('okx_set_pwd', 'Re-enter Password')
            self.page.wait(1)
            ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text():Confirm', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.logit('okx_set_pwd', 'Password Confirmed [OK]')
                return True
        return False

    def okx_bulk_import_private_key(self, s_key):
        ele_btn = self.page.ele('@@tag()=div@@class:_typography@@text():Bulk import private key', timeout=2) # noqa
        if not isinstance(ele_btn, NoneElement):
            ele_btn.click(by_js=True)
            self.logit('okx_bulk_import_private_key', 'Click ...')

            self.page = self.page.get_tab(self.page.latest_tab.tab_id)

            ele_btn = self.page.ele('@@tag()=i@@id=okdDialogCloseBtn', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                self.logit(None, 'Close pwd input box ...')
                ele_btn.click(by_js=True)

            ele_btn = self.page.ele('@@tag()=div@@data-testid=okd-select-reference-value-box', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                self.logit(None, 'Select network ...')
                ele_btn.click(by_js=True)

            ele_btn = self.page.ele('@@tag()=div@@class:_typography@@text()=EVM networks', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                self.logit(None, 'Click EVM networks ...')
                ele_btn.click(by_js=True)

            ele_input = self.page.ele('@@tag()=textarea@@id:pk-input@@placeholder:private', timeout=2) # noqa
            if not isinstance(ele_input, NoneElement):
                self.logit(None, 'Click EVM networks ...')
                self.page.actions.move_to(ele_input).click().type(s_key) # noqa
                self.page.wait(5)

    def init_okx(self, is_bulk=False):
        """
        chrome-extension://jiofmdifioeejeilfkpegipdjiopiekl/popup/index.html
        """
        # self.check_start_tabs()
        s_url = f'chrome-extension://{EXTENSION_ID_OKX}/home.html'
        self.page.get(s_url)
        # self.page.wait.load_start()
        self.page.wait(3)
        self.close_popup_tabs()
        self.check_start_tabs('OKX Wallet', 'precise')

        self.logit('init_okx', f'tabs_count={self.page.tabs_count}')

        self.save_screenshot(name='okx_1.jpg')

        ele_info = self.page.ele('@@tag()=div@@class:balance', timeout=2) # noqa
        if not isinstance(ele_info, NoneElement):
            s_info = ele_info.text
            self.logit('init_okx', f'Account balance: {s_info}') # noqa
            return True

        ele_btn = self.page.ele('Import wallet', timeout=2)
        if not isinstance(ele_btn, NoneElement):
            # Import wallet
            self.logit('init_okx', 'Import wallet ...')
            ele_btn.click(by_js=True)

            self.page.wait(1)
            ele_btn = self.page.ele('Seed phrase or private key', timeout=2)
            if not isinstance(ele_btn, NoneElement):
                # Import wallet
                self.logit('init_okx', 'Select Seed phrase or private key ...') # noqa
                ele_btn.click(by_js=True)
                self.page.wait(1)

                s_key = self.dic_purse[self.args.s_profile][1]
                if len(s_key.split()) == 1:
                    # Private key
                    self.logit('init_okx', 'Import By Private key')
                    ele_btn = self.page.ele('Private key', timeout=2)
                    if not isinstance(ele_btn, NoneElement):
                        # 点击 Private key Button
                        self.logit('init_okx', 'Select Private key')
                        ele_btn.click(by_js=True)
                        self.page.wait(1)
                        ele_input = self.page.ele('@class:okui-input-input input-textarea ta', timeout=2) # noqa
                        if not isinstance(ele_input, NoneElement):
                            # 使用动作，输入完 Confirm 按钮才会变成可点击状态
                            self.page.actions.move_to(ele_input).click().type(s_key) # noqa
                            self.page.wait(5)
                            self.logit('init_okx', 'Input Private key')
                    is_bulk = True
                    if is_bulk:
                        self.okx_bulk_import_private_key(s_key)
                else:
                    # Seed phrase
                    self.logit('init_okx', 'Import By Seed phrase')
                    words = s_key.split()

                    # 输入助记词需要最大化窗口，否则最后几个单词可能无法输入
                    self.page.set.window.max()

                    ele_inputs = self.page.eles('.mnemonic-words-inputs__container__input', timeout=2) # noqa
                    if not isinstance(ele_inputs, NoneElement):
                        self.logit('init_okx', 'Input Seed phrase')
                        for i in range(len(ele_inputs)):
                            ele_input = ele_inputs[i]
                            self.page.actions.move_to(ele_input).click().type(words[i]) # noqa
                            self.logit(None, f'Input word [{i+1}/{len(words)}]') # noqa
                            self.page.wait(1)

                # Confirm
                max_wait_sec = 10
                i = 1
                while i < max_wait_sec:
                    ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text():Confirm', timeout=2) # noqa
                    self.logit('init_okx', f'To Confirm ... {i}/{max_wait_sec}') # noqa
                    if not isinstance(ele_btn, NoneElement):
                        if ele_btn.states.is_enabled is False:
                            self.logit(None, 'Confirm Button is_enabled=False')
                        else:
                            if ele_btn.states.is_clickable:
                                ele_btn.click(by_js=True)
                                self.logit('init_okx', 'Confirm Button is clicked') # noqa
                                self.page.wait(1)
                                break
                            else:
                                self.logit(None, 'Confirm Button is_clickable=False') # noqa

                    i += 1
                    self.page.wait(1)
                # 未点击 Confirm
                if i >= max_wait_sec:
                    self.logit('init_okx', 'Confirm Button is not found [ERROR]') # noqa

                # 导入私钥有此选择页面，导入助记词则没有此选择过程
                # Select network and Confirm
                ele_info = self.page.ele('Select network', timeout=2)
                if not isinstance(ele_info, NoneElement):
                    self.logit('init_okx', 'Select network ...')
                    ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        self.page.wait(1)
                        self.logit('init_okx', 'Select network finish')

                self.okx_secure_wallet()

                # Set password
                is_success = self.okx_set_pwd()

                # Start your Web3 journey
                self.page.wait(1)
                self.save_screenshot(name='okx_2.jpg')
                ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text():Start', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.logit('init_okx', 'import wallet success')
                    self.save_screenshot(name='okx_3.jpg')
                    self.page.wait(2)

                if is_success:
                    return True
        else:
            ele_info = self.page.ele('Your portal to Web3', timeout=2)
            if not isinstance(ele_info, NoneElement):
                self.logit('init_okx', 'Input password to unlock ...')
                s_path = '@@tag()=input@@data-testid=okd-input@@placeholder:Enter' # noqa
                ele_input = self.page.ele(s_path, timeout=2) # noqa
                if not isinstance(ele_input, NoneElement):
                    self.page.actions.move_to(ele_input).click().type(DEF_PWD)
                    if ele_input.value != DEF_PWD:
                        self.logit('init_okx', '[ERROR] Fail to input passwrod !') # noqa
                        self.page.set.window.max()
                        return False

                    self.page.wait(1)
                    ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text():Unlock', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        self.page.wait(1)

                        self.logit('init_okx', 'login success')
                        self.save_screenshot(name='okx_2.jpg')

                        return True
            else:
                ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text()=Approve', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.page.wait(1)
                else:
                    ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text()=Connect', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        self.page.wait(1)
                    else:
                        self.logit('init_okx', '[ERROR] What is this ... [quit]') # noqa
                        self.page.quit()

        self.logit('init_okx', 'login failed [ERROR]')
        return False

    def okx_confirm(self):
        # OKX Wallet Confirm
        max_retry = 5
        max_wait_sec = 15
        self.logit('okx_confirm', None) # noqa
        # pdb.set_trace()

        def set_fee(tab_new, s_info_fee, val_fee):
            """
            s_info_fee:
                Max base fee
                Priority fee
            val_fee:
                DEF_FEE_MAX_BASE
                DEF_FEE_PRIORITY
            """
            self.logit('set_fee', s_info_fee) # noqa
            i = 0
            while i < max_wait_sec:
                i += 1
                s_path = f'@@tag()=div@@class=okui-input okui-input-md@@text()={s_info_fee}' # noqa
                ele_block = tab_new.ele(s_path, timeout=2)
                if not isinstance(ele_block, NoneElement):
                    ele_input = ele_block.ele('@@tag()=input@@data-testid=okd-input', timeout=2) # noqa
                    if not isinstance(ele_input, NoneElement):
                        # 取消该判断，如果之前改得太小，有此判断，就没法再改大了
                        # if float(ele_input.value) <= float(val_fee):
                        #     self.logit(None, f'{s_info_fee} {ele_input.value} <= {val_fee} Not Modify') # noqa
                        #     return True

                        self.logit(None, f'{s_info_fee} fee={ele_input.value} Before Modify') # noqa
                        ele_input.click.multi(times=2)
                        tab_new.actions.type('BACKSPACE')
                        tab_new.actions.move_to(ele_input).click().type(val_fee) # noqa
                        if ele_input.value == val_fee:
                            self.logit(None, f'{s_info_fee} fee={ele_input.value} Modify Success') # noqa
                        return True
                else:
                    if self.cancel_estimation_unsuccess(tab_new):
                        return False
                self.page.wait(1)
            return False

        i = 0
        while i < max_retry:
            i += 1
            if len(self.page.tab_ids) == 2:
                tab_id = self.page.latest_tab
                tab_new = self.page.get_tab(tab_id)

                for j in range(max_wait_sec):
                    ele_btn = tab_new.ele('@@tag()=div@@text()=Est Botanix Testnet network fee', timeout=2) # noqa
                    self.logit(None, f'{j}/{max_wait_sec} Modify network fee ...') # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        self.logit(None, f'{j}/{max_wait_sec} Modify network fee [Clicked]') # noqa
                        break
                    self.page.wait(1)
                if j >= max_wait_sec:
                    self.logit(None, f'{j}/{max_wait_sec} Modify network fee Failed') # noqa
                    continue

                if not set_fee(tab_new, 'Max base fee', DEF_FEE_MAX_BASE):
                    continue
                if not set_fee(tab_new, 'Priority fee', DEF_FEE_PRIORITY):
                    continue

                # Save these values as default for Botanix Testnet
                ele_chkbox = tab_new.ele('@@tag()=input@@type=checkbox@@class=okui-checkbox-input', timeout=2) # noqa
                if not isinstance(ele_chkbox, NoneElement):
                    if ele_chkbox.states.is_checked is False:
                        ele_chkbox.click(by_js=True)

                # Network fee Confirm
                ele_block = tab_new.ele('@@tag()=div@@class:affix@@text():Save these values', timeout=2) # noqa
                if not isinstance(ele_block, NoneElement):
                    ele_btn = ele_block.ele('@@tag()=button@@data-testid=okd-button@@text()=Confirm', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        self.logit(None, 'Network fee Confirmed [OK]')

                # Tranction Confirm
                ele_block = tab_new.ele('@@tag()=div@@class:affix@@text():Cancel', timeout=2) # noqa
                if not isinstance(ele_block, NoneElement):
                    ele_btn = ele_block.ele('@@tag()=button@@data-testid=okd-button@@text()=Confirm', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        self.logit(None, 'Tranction Confirmed [OK]')
                        return True
                break
            else:
                self.page.wait(1)
        if i >= max_wait_sec:
            self.logit('okx_confirm', f'没有出现 Confirm 弹窗, took {i} seconds.')

        return False

    def save_screenshot(self, name):
        # 对整页截图并保存
        # self.page.set.window.max()
        s_name = f'{self.args.s_profile}_{name}'
        self.page.get_screenshot(path='tmp_img', name=s_name, full_page=True)

    def update_status(self, update_ts=None):
        if not update_ts:
            update_ts = time.time()
        update_time = format_ts(update_ts, 2, TZ_OFFSET)
        if self.args.s_profile in self.dic_status:
            self.dic_status[self.args.s_profile][1] = update_time
        else:
            self.dic_status[self.args.s_profile] = [
                self.args.s_profile,
                update_time
            ]
        self.status_save()
        self.is_update = True

    def okx_cancel(self):
        max_retry = 5
        max_wait_sec = 30
        i = 0
        while i < max_retry:
            i += 1
            if len(self.page.tab_ids) == 2:
                self.logit('okx_cancel', f'New popup window ... {i}/{max_wait_sec}') # noqa
                tab_id = self.page.latest_tab
                tab_new = self.page.get_tab(tab_id)

                for j in range(max_wait_sec):
                    ele_btn = tab_new.ele('@@tag()=div@@text(): confirmations', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        n_trans = extract_numbers(ele_btn.text)[1]
                        self.logit('okx_cancel', f'[confirmations={n_trans}]') # noqa
                        if n_trans > 1:
                            ele_btn = tab_new.ele('@@tag()=button@@data-testid=okd-button@@text():Cancel', timeout=2) # noqa
                            if not isinstance(ele_btn, NoneElement):
                                ele_btn.click(by_js=True)
                                self.logit('okx_cancel', f'[confirmations={n_trans}] Cancel transaction ...') # noqa
                                self.page.wait(1)
                                continue
                        else:
                            return True
                    else:
                        self.logit('okx_cancel', 'check confirmations [OK]') # noqa
                        return False
                if j >= max_wait_sec:
                    self.logit('okx_cancel', f'okx_cancel Failed [{j}/{max_wait_sec}]') # noqa
                    continue
                # 有弹窗，就不再循环
                break
            else:
                self.logit('okx_cancel', f'Wait popup window ... {i}/{max_wait_sec}') # noqa
                # 没有弹窗，重试
                self.page.wait(1)
        return False

    def cancel_estimation_unsuccess(self, tab_new):
        ele_info = tab_new.ele('Estimation unsuccessful', timeout=2)
        if not isinstance(ele_info, NoneElement):
            self.logit(None, 'Estimation unsuccessful ...')
            ele_btn = tab_new.ele('@@tag()=button@@data-testid=okd-button@@text():Cancel', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.logit(None, f'Cancel unestimation transaction ...') # noqa
                self.page.wait(1)
                return True
        return False

    def testnet_mint(self, coin):
        """
        coin:
            USDC
            WBTC
        """
        self.logit('testnet_mint', f'########## [Mint {coin}]') # noqa

        # self.page.get('https://dev.app.spindlefinance.xyz/mint')
        # self.page.wait(2)

        ele_block = self.page.ele(f'@@tag()=div@@class:relative flex w-full@@text():Testnet {coin}', timeout=2) # noqa
        if not isinstance(ele_block, NoneElement):
            ele_btn = ele_block.ele('@@tag()=button@@text()=Mint', timeout=2)
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.page.wait(1)

                # 确认是否有待取消的交易
                self.logit('testnet_mint', '##### okx_cancel ...') # noqa
                self.okx_cancel()

                # OKX Wallet Confirm
                self.logit('testnet_mint', '##### okx_confirm ...') # noqa
                if not self.okx_confirm():
                    self.logit(None, 'transaction failed.') # noqa
                    return False

                max_wait_sec = 30
                i = 0
                while i < max_wait_sec:
                    i += 1
                    self.save_screenshot(name=f'mint_{coin}_001.jpg')
                    # ele_info = self.page.ele('@@tag()=div@@text()=Transaction successful', timeout=2) # noqa
                    ele_info = self.page.ele('@@tag()=div@@class=text-sm font-semibold', timeout=2) # noqa
                    if not isinstance(ele_info, NoneElement):
                        self.save_screenshot(name=f'mint_{coin}_002.jpg')
                        s_info = ele_info.text
                        self.logit(None, f'----- Status: {s_info} [{i}/{max_wait_sec}]') # noqa
                        if s_info == 'Transaction in progress':
                            self.page.wait(1)
                        else:
                            ele_btn = self.page.ele('@@tag()=button@@class:absolute', timeout=2) # noqa
                            if not isinstance(ele_btn, NoneElement):
                                ele_btn.click(by_js=True)
                                self.logit(None, f'Close Toast ({s_info})') # noqa
                                self.save_screenshot(name=f'mint_{coin}_003.jpg') # noqa

                            if s_info == 'Transaction failed':
                                return False

                            # Transaction successful
                            # Unknown error occurred
                            # 两种情况，都是提交成功，交易处于 Pending ，提示是 Unknown error occurred # noqa
                            self.update_status()
                            return True
                    else:
                        self.logit(None, f'----- Get Transaction result ... [{i}/{max_wait_sec}]') # noqa

                if i >= max_wait_sec:
                    self.logit('testnet_mint', f'Transaction failed, took {i} seconds.') # noqa
                    return False
        return False

    def spindle_lend(self, coin):
        """
        coin:
            USDC
            WBTC
        """

        def select_ammount(ammount='Max'):
            """
            ammount:
                Max
                50%
            """
            ele_btn = self.page.ele(f'@@tag()=button@@text()={ammount}', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.logit(None, f'Click {ammount} Button') # noqa
                self.page.wait(1)
                return True
            return False

        def click_button(button_info):
            """
            button_info:
                Approve
                Lend
            """
            max_retry = 5
            i = 0
            while i < max_retry:
                i += 1
                ele_btn = self.page.ele(f'@@tag()=button@@text()={button_info}', timeout=2) # noqa
                self.logit(None, f'Ready To {button_info} ... {i}/{max_retry}') # noqa
                if not isinstance(ele_btn, NoneElement):
                    if ele_btn.states.is_enabled is False:
                        self.logit(None, f'{button_info} Button is_enabled=False') # noqa
                    else:
                        if ele_btn.states.is_clickable:
                            ele_btn.click(by_js=True)
                            self.logit(None, f'{button_info} Button is clicked') # noqa
                            self.page.wait(1)

                            # 确认是否有待取消的交易
                            # self.logit(None, '##### okx_cancel ...') # noqa
                            self.okx_cancel()

                            # OKX Wallet Confirm
                            self.logit(None, '##### okx_confirm ...') # noqa
                            if not self.okx_confirm():
                                self.logit(None, 'Transaction is failed.') # noqa
                                continue

                            n_wait_sec = 20
                            j = 0
                            while j < n_wait_sec:
                                j += 1
                                ele_info = self.page.ele('@@tag()=div@@class=text-sm font-semibold', timeout=2) # noqa
                                if not isinstance(ele_info, NoneElement):
                                    s_info = ele_info.text
                                    self.logit(None, f'----- Status: {s_info} [{j}/{n_wait_sec}]') # noqa
                                    if s_info == 'Transaction in progress':
                                        self.page.wait(1)
                                    else:
                                        ele_btn = self.page.ele('@@tag()=button@@class:absolute', timeout=2) # noqa
                                        if not isinstance(ele_btn, NoneElement): # noqa
                                            ele_btn.click(by_js=True)
                                            self.logit(None, f'Close Toast ({s_info})') # noqa

                                        if s_info == 'Transaction failed':
                                            return False

                                        # Transaction successful
                                        # Unknown error occurred
                                        # 两种情况，都是提交成功，交易处于 Pending ，提示是 Unknown error occurred # noqa
                                        return True
                                else:
                                    self.logit(None, f'----- Get Transaction result ... [{j}/{n_wait_sec}]') # noqa

                            if j >= n_wait_sec:
                                self.logit('spindle_lend', f'Transaction failed, took {j} seconds.') # noqa
                                return False
                            break
                        else:
                            self.logit(None, 'Confirm Button is_clickable=False') # noqa

                self.page.wait(1)
            # 未点击 Confirm
            if i >= max_retry:
                self.logit('spindle_lend', 'Confirm Button is not found [ERROR]') # noqa

            return False


        for i in range(1, DEF_NUM_TRY):
            self.logit('spindle_lend', f'try_i={i}/{DEF_NUM_TRY}')

            if self.init_okx() is False:
                continue

            s_url = 'https://dev.app.spindlefinance.xyz/lend'
            self.page.get(s_url)
            self.page.wait(3)
            self.logit('spindle_lend', s_url)

            self.terms_accept()

            self.logit('spindle_lend', f'tabs_count={self.page.tabs_count}')

            ele_btn = self.page.ele(f'@@tag()=div@@text()={coin}', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.logit(None, f'Lend ({coin})') # noqa
                self.page.wait(2)

            ele_info = self.page.ele('@@tag()=div@@class=flex items-center justify-between text-muted-foreground@@text():Wallet balance', timeout=2) # noqa
            if not isinstance(ele_info, NoneElement):
                s_info = ele_info.text.replace('\n', ' ')
                self.logit(None, f's_info: {s_info}') # noqa
                # 使用正则表达式提取数字
                match = re.search(r'(\d+\.\d+)', s_info)
                if match:
                    balance = match.group(1)
                    try:
                        balance = float(balance)
                    except: # noqa
                        balance = 0
                    if balance <= 0.0000001:
                        # 余额不足
                        return DEF_INSUFFICIENT
                else:
                    self.logit(None, 'Fail to get wallet balance') # noqa
                    continue

            # Click MAX Button / 50% Button
            if not select_ammount('Max'):
                continue

            # Click Approve Button
            click_button('Approve')

            if not select_ammount('50%'):
                continue
            if not select_ammount('Max'):
                continue

            # Click Lend Button
            if click_button('Lend'):
                self.update_status()
                return DEF_SUCCESS
        return DEF_FAIL

    def terms_accept(self):
        ele_info = self.page.ele('Terms of Services', timeout=2)
        if not isinstance(ele_info, NoneElement):
            self.logit('spindle_mint', 'Terms of Services [Select]') # noqa
            ele_btn = self.page.ele('@@tag()=button@@role=checkbox', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.page.wait(1)

                ele_btn = self.page.ele('@@tag()=button@@text()=Accept', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.page.wait(1)

    def spindle_mint(self, coin=None):
        """
        coin:
            USDC: only mint USDC
            WBTC: only mint WBTC
            Default: Mint USDC and WBTC
        """
        for i in range(1, DEF_NUM_TRY):
            self.logit('spindle_mint', f'Faucet Summit try_i={i}/{DEF_NUM_TRY}')

            if self.init_okx() is False:
                continue

            self.page.get('https://dev.app.spindlefinance.xyz/mint')
            # self.page.wait.load_start()
            self.page.wait(3)

            self.logit('spindle_mint', f'tabs_count={self.page.tabs_count}')

            self.terms_accept()

            # 钱包未连接
            ele_btn = self.page.ele('@@tag()=button@@text()=Connect Wallet', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                self.logit('spindle_mint', 'Need to Connect Wallet ...') # noqa
                ele_btn.click(by_js=True)
                self.page.wait(1)
                ele_btn = self.page.ele('@@tag()=div@@class:iekbcc0 ju367v4@@text()=OKX Wallet', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.page.wait(1)

                    # OKX Wallet Connect
                    self.save_screenshot(name='page_wallet_connect.jpg')
                    if len(self.page.tab_ids) == 2:
                        tab_id = self.page.latest_tab
                        tab_new = self.page.get_tab(tab_id)
                        ele_btn = tab_new.ele('@@tag()=button@@data-testid=okd-button@@text()=Connect', timeout=2) # noqa
                        if not isinstance(ele_btn, NoneElement):
                            ele_btn.click(by_js=True)
                            self.page.wait(1)

                    # OKX Wallet Add network
                    if len(self.page.tab_ids) == 2:
                        tab_id = self.page.latest_tab
                        tab_new = self.page.get_tab(tab_id)
                        ele_btn = tab_new.ele('@@tag()=button@@data-testid=okd-button@@text()=Approve', timeout=2) # noqa
                        if not isinstance(ele_btn, NoneElement):
                            ele_btn.click(by_js=True)
                            self.page.wait(1)

            # Wrong network
            ele_btn = self.page.ele('@@tag()=button@@text()=Wrong network', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                self.logit('spindle_mint', 'Wrong network ...')
                ele_btn.click(by_js=True)
                self.page.wait(1)
                ele_btn = self.page.ele('@@tag()=button@@text()=Botanix Testnet', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    self.logit('spindle_mint', 'Select Botanix Testnet ...')
                    ele_btn.click(by_js=True)
                    self.page.wait(1)

                    # Approve
                    if len(self.page.tab_ids) == 2:
                        tab_id = self.page.latest_tab
                        tab_new = self.page.get_tab(tab_id)
                        ele_btn = tab_new.ele('@@tag()=button@@data-testid=okd-button@@text()=Approve', timeout=2) # noqa
                        if not isinstance(ele_btn, NoneElement):
                            ele_btn.click(by_js=True)
                            self.logit('spindle_mint', 'Approve Botanix Testnet ...') # noqa
                            self.page.wait(1)

            # 钱包已连接
            ele_btn = self.page.ele('@@tag()=button@@class:inline-flex items-center@@text():…', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                self.logit('spindle_mint', 'Wallet is connected')
            else:
                self.logit('spindle_mint', 'Wallet is failed to connected [ERROR]') # noqa
                continue

            if coin is None:
                is_success = False
                n_mint = random.randint(DEF_MINT_USDC_MIN, DEF_MINT_USDC_MAX)
                for i in range(n_mint):
                    self.logit('spindle_mint', f'*** Mint USDC {i+1}/{n_mint}')
                    ret = self.testnet_mint('USDC')
                    is_success = is_success or ret

                n_mint = random.randint(DEF_MINT_WBTC_MIN, DEF_MINT_WBTC_MAX)
                for i in range(n_mint):
                    self.logit('spindle_mint', f'*** Mint WBTC {i+1}/{n_mint}')
                    ret = self.testnet_mint('WBTC')
                    is_success = is_success or ret
            else:
                if coin == 'USDC':
                    n_mint = random.randint(DEF_MINT_USDC_MIN, DEF_MINT_USDC_MAX)
                elif coin == 'WBTC':
                    n_mint = random.randint(DEF_MINT_WBTC_MIN, DEF_MINT_WBTC_MAX)
                else:
                    self.logit('spindle_mint', f'Not Support! coin={coin} Error!')
                    sys.exit(1)

                for i in range(n_mint):
                    self.logit('spindle_mint', f'*** Mint {coin} {i+1}/{n_mint}')
                    is_success = self.testnet_mint(coin)

            if is_success:
                logger.info('Mint success!')
                self.logit('spindle_mint', 'Mint success!')
                return True

        self.logit('spindle_mint', 'Mint failed!')
        self.close()
        return False

    def get_pending_num(self, s):
        # 使用正则表达式匹配括号内的数字
        match = re.search(r'\((\d+)\)', s)
        if match:
            # 如果匹配成功，提取数字并转换为整数
            return int(match.group(1))
        else:
            # 如果未匹配到数字，返回-1
            return -1

    def is_tx_pending(self):
        s_url = f'chrome-extension://{EXTENSION_ID_OKX}/home.html'
        self.page.get(s_url)
        # self.page.wait.load_start()
        self.page.wait(3)

        ele_btn = self.page.ele('@@tag()=div@@class=_container_1eikt_1', timeout=2) # noqa
        if not isinstance(ele_btn, NoneElement):
            ele_btn.click(by_js=True)
            self.page.wait(1)

        # Search network name
        ele_input = self.page.ele('@@tag()=input@@data-testid=okd-input', timeout=2) # noqa
        if not isinstance(ele_input, NoneElement):
            self.logit('is_tx_exist', 'Change network to Botanix Testnet ...') # noqa
            self.page.actions.move_to(ele_input).click().type('botanix')
            self.page.wait(3)
            ele_btn = self.page.ele('@@tag()=div@@class:_title@@text()=Botanix Testnet', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.page.wait(3)

                # History
                ele_blk = self.page.ele(f'@@tag()=div@@class:_iconWrapper_@@text()=History', timeout=2) # noqa
                if not isinstance(ele_blk, NoneElement):
                    self.logit(None, 'Click History ...') # noqa
                    ele_btn = ele_blk.ele('@@tag()=div@@class:_wallet', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        self.page.wait(2)

                        # Pending 如果不是0，需要等待
                        ele_info = self.page.ele('@@tag()=div@@class:tx-history__tabs-option@@text():Pending', timeout=2) # noqa
                        if not isinstance(ele_info, NoneElement):
                            s_info = ele_info.text
                            self.logit(None, f'[History Pending] {s_info}')
                            n_pending = self.get_pending_num(s_info)
                            if n_pending > 0:
                                n_sleep = 2
                                self.logit(None, f'⚠️ [WARNING] tx is Pending: {s_info} Sleep {n_sleep} seconds') # noqa
                                self.page.wait(n_sleep)

                                ele_btn = self.page.ele('@@tag()=i@@class:icon iconfont okx-wallet-plugin-brush@@role=button', timeout=2) # noqa
                                if not isinstance(ele_btn, NoneElement):
                                    ele_btn.click(by_js=True)
                                    self.logit(None, 'Reset Nonce and clear pending transactions') # noqa
                                    self.page.wait(1)
                                    ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-dialog-confirm-btn@@text()=Confirm', timeout=2) # noqa
                                    if not isinstance(ele_btn, NoneElement):
                                        ele_btn.click(by_js=True)
                                        self.logit(None, 'Clear pending tx Confirmed [OK]')
                                        return True
                            else:
                                self.logit(None, '✅ No pending tx') # noqa
                                return True
        else:
            # Cancel Uncomplete request
            ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text():Cancel', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.page.wait(1)
                self.logit(None, 'Uncomplete request. Cancel')

        return True

    def spindle_run(self):
        if self.init_okx() is False:
            self.logit(None, 'Fail to init okx')
        self.is_tx_pending()

        n_raffle = random.randint(1, 5)
        # n_raffle = 1
        self.logit('spindle_run', f'n_raffle={n_raffle}')

        if n_raffle == 1:
            if self.spindle_lend('USDC') != DEF_SUCCESS:
                self.spindle_mint('USDC')
        elif n_raffle == 2:
            if self.spindle_lend('WBTC') != DEF_SUCCESS:
                self.spindle_mint('WBTC')
        elif n_raffle == 3:
            self.spindle_mint('USDC')
        elif n_raffle == 4:
            self.spindle_mint('WBTC')
        elif n_raffle == 5:
            self.spindle_mint()
        else:
            self.logit('spindle_run', f'n_raffle={n_raffle} is error !')
            sys.exit(1)

        return True


def send_msg(instSpindleTask, lst_success):
    if len(DEF_DING_TOKEN) > 0 and len(lst_success) > 0:
        s_info = ''
        for s_profile in lst_success:
            if s_profile in instSpindleTask.dic_status:
                lst_status = instSpindleTask.dic_status[s_profile]
            else:
                lst_status = [s_profile, -1]

            s_info += '- {} {}\n'.format(
                s_profile,
                lst_status[1],
            )
        d_cont = {
            'title': 'Daily Active Finished! [spindlefinance]',
            'text': (
                'Daily Active [spindlefinance]\n'
                '- {}\n'
                '{}\n'
                .format(DEF_HEADER_STATUS, s_info)
            )
        }
        ding_msg(d_cont, DEF_DING_TOKEN, msgtype="markdown")


def main(args):
    if args.sleep_sec_at_start > 0:
        logger.info(f'Sleep {args.sleep_sec_at_start} seconds at start !!!') # noqa
        time.sleep(args.sleep_sec_at_start)

    if DEL_PROFILE_DIR and os.path.exists(DEF_PATH_USER_DATA):
        logger.info(f'Delete {DEF_PATH_USER_DATA} ...')
        shutil.rmtree(DEF_PATH_USER_DATA)
        logger.info(f'Directory {DEF_PATH_USER_DATA} is deleted') # noqa

    instSpindleTask = SpindleTask()

    if len(args.profile) > 0:
        items = args.profile.split(',')
    else:
        # 从配置文件里获取钱包名称列表
        items = list(instSpindleTask.dic_purse.keys())

    profiles = copy.deepcopy(items)

    # 每次随机取一个出来，并从原列表中删除，直到原列表为空
    total = len(profiles)
    n = 0

    lst_success = []

    # 将已完成的剔除掉
    instSpindleTask.status_load()
    # 从后向前遍历列表的索引
    for i in range(len(profiles) - 1, -1, -1):
        s_profile = profiles[i]
        if s_profile in instSpindleTask.dic_status:
            lst_status = instSpindleTask.dic_status[s_profile]
            if lst_status:
                avail_time = lst_status[1]
                if avail_time:
                    date_now = format_ts(time.time(), style=1, tz_offset=TZ_OFFSET) # noqa
                    date_account = avail_time[:10]
                    if date_now == date_account:
                        n += 1
                        profiles.pop(i)
        else:
            continue
    logger.info('#'*40)
    percent = math.floor((n / total) * 100)
    logger.info(f'Progress: {percent}% [{n}/{total}]') # noqa

    while profiles:
        n += 1
        logger.info('#'*40)
        s_profile = random.choice(profiles)
        percent = math.floor((n / total) * 100)
        logger.info(f'Progress: {percent}% [{n}/{total}] [{s_profile}]') # noqa
        profiles.remove(s_profile)

        args.s_profile = s_profile

        if s_profile not in instSpindleTask.dic_purse:
            logger.info(f'{s_profile} is not in purse conf [ERROR]')
            sys.exit(0)

        def _run():
            s_directory = f'{DEF_PATH_USER_DATA}/{args.s_profile}'
            if os.path.exists(s_directory) and os.path.isdir(s_directory):
                pass
            else:
                # Create new profile
                instSpindleTask.initChrome(args.s_profile)
                instSpindleTask.init_okx()
                instSpindleTask.close()

            instSpindleTask.initChrome(args.s_profile)
            is_claim = instSpindleTask.spindle_run()
            return is_claim

        # 如果出现异常(与页面的连接已断开)，增加重试
        max_try_except = 3
        for j in range(1, max_try_except+1):
            try:
                is_claim = False
                if j > 1:
                    logger.info(f'异常重试，当前是第{j}次执行，最多尝试{max_try_except}次 [{s_profile}]') # noqa

                instSpindleTask.set_args(args)
                instSpindleTask.status_load()

                if s_profile in instSpindleTask.dic_status:
                    lst_status = instSpindleTask.dic_status[s_profile]
                else:
                    lst_status = None

                is_claim = False
                is_ready_claim = True
                if lst_status:
                    avail_time = lst_status[1]
                    if avail_time:
                        date_now = format_ts(time.time(), style=1, tz_offset=TZ_OFFSET) # noqa
                        date_account = avail_time[:10]
                        if date_now == date_account:
                            logger.info(f'[{s_profile}] Last update at {avail_time}') # noqa
                            is_ready_claim = False
                            break
                if is_ready_claim:
                    is_claim = _run()

                if is_claim:
                    lst_success.append(s_profile)
                    instSpindleTask.close()
                    break

            except Exception as e:
                logger.info(f'[{s_profile}] An error occurred: {str(e)}')
                instSpindleTask.close()
                if j < max_try_except:
                    time.sleep(5)

        if instSpindleTask.is_update is False:
            continue

        logger.info(f'Progress: {percent}% [{n}/{total}] [{s_profile} Finish]')

        if len(items) > 0:
            sleep_time = random.randint(args.sleep_sec_min, args.sleep_sec_max)
            if sleep_time > 60:
                logger.info('sleep {} minutes ...'.format(int(sleep_time/60)))
            else:
                logger.info('sleep {} seconds ...'.format(int(sleep_time)))
            time.sleep(sleep_time)

    send_msg(instSpindleTask, lst_success)


if __name__ == '__main__':
    """
    每次随机取一个出来，并从原列表中删除，直到原列表为空
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--loop_interval', required=False, default=60, type=int,
        help='[默认为 60] 执行完一轮 sleep 的时长(单位是秒)，如果是0，则不循环，只执行一次'
    )
    parser.add_argument(
        '--sleep_sec_min', required=False, default=3, type=int,
        help='[默认为 3] 每个账号执行完 sleep 的最小时长(单位是秒)'
    )
    parser.add_argument(
        '--sleep_sec_max', required=False, default=10, type=int,
        help='[默认为 10] 每个账号执行完 sleep 的最大时长(单位是秒)'
    )
    parser.add_argument(
        '--sleep_sec_at_start', required=False, default=0, type=int,
        help='[默认为 0] 在启动后先 sleep 的时长(单位是秒)'
    )
    parser.add_argument(
        '--profile', required=False, default='',
        help='按指定的 profile 执行，多个用英文逗号分隔'
    )
    args = parser.parse_args()
    if args.loop_interval <= 0:
        main(args)
    else:
        while True:
            main(args)
            logger.info('#####***** Loop sleep {} seconds ...'.format(args.loop_interval)) # noqa
            time.sleep(args.loop_interval)

"""
python3 spindle.py --sleep_sec_min=30 --sleep_sec_max=60 --loop_interval=60
python3 spindle.py --sleep_sec_min=600 --sleep_sec_max=1800 --loop_interval=60
"""
