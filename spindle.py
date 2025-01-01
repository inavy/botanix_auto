import os # noqa
import sys # noqa
import argparse
import random
import time
import copy
import pdb # noqa
import shutil
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
            self.page.quit()

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

    def init_okx(self):
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
                            self.page.wait(1)
                            self.logit('init_okx', 'Input Private key')
                else:
                    # Seed phrase
                    self.logit('init_okx', 'Import By Seed phrase')
                    words = s_key.split()

                    ele_inputs = self.page.eles('.mnemonic-words-inputs__container__input', timeout=2) # noqa
                    if not isinstance(ele_inputs, NoneElement):
                        self.logit('init_okx', 'Input Seed phrase')
                        for i in range(len(ele_inputs)):
                            ele_input = ele_inputs[i]
                            self.page.actions.move_to(ele_input).click().type(words[i]) # noqa

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
                ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text():Start', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.logit('init_okx', 'import wallet success')
                    self.save_screenshot(name='okx_2.jpg')

                if is_success:
                    return True
        else:
            ele_info = self.page.ele('Your portal to Web3', timeout=2)
            if not isinstance(ele_info, NoneElement):
                self.logit('init_okx', 'Input password to unlock ...')
                ele_input = self.page.ele('@@tag()=input@@data-testid=okd-input@@placeholder:Enter', timeout=2) # noqa
                if not isinstance(ele_input, NoneElement):
                    self.page.actions.move_to(ele_input).click().type(DEF_PWD)
                    self.page.wait(1)
                    ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text():Unlock', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        self.page.wait(1)

                        self.logit('init_okx', 'login success')
                        self.save_screenshot(name='okx_2.jpg')

                        return True

        self.logit('init_okx', 'login failed [ERROR]')
        return False

    def okx_confirm(self):
        # OKX Wallet Confirm
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
            i = 1
            while i < max_wait_sec:
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
                self.page.wait(1)
            return False

        i = 1
        while i < max_wait_sec:
            if len(self.page.tab_ids) == 2:
                tab_id = self.page.latest_tab
                tab_new = self.page.get_tab(tab_id)

                for i in range(max_wait_sec):
                    ele_btn = tab_new.ele('@@tag()=div@@text()=Est Botanix Testnet network fee', timeout=2) # noqa
                    self.logit(None, f'{i}/{max_wait_sec} Modify network fee ...') # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        break
                    self.page.wait(1)
                if i >= max_wait_sec:
                    self.logit(None, f'{i}/{max_wait_sec} Modify network fee Failed') # noqa
                    continue

                set_fee(tab_new, 'Max base fee', DEF_FEE_MAX_BASE)
                set_fee(tab_new, 'Priority fee', DEF_FEE_PRIORITY)

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
        max_wait_sec = 30
        i = 1
        while i < max_wait_sec:
            if len(self.page.tab_ids) == 2:
                tab_id = self.page.latest_tab
                tab_new = self.page.get_tab(tab_id)

                for i in range(max_wait_sec):
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
                if i >= max_wait_sec:
                    self.logit('okx_cancel', f'okx_cancel Failed [{i}/{max_wait_sec}]') # noqa
                    continue
                # 有弹窗，就不再循环
                break
            else:
                # 没有弹窗，重试
                self.page.wait(1)
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
                self.okx_confirm()

                max_wait_sec = 30
                i = 1
                while i < max_wait_sec:
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

                            # Transaction successful
                            # Unknown error occurred
                            # 两种情况，都是提交成功，交易处于 Pending ，提示是 Unknown error occurred # noqa
                            self.update_status()
                            return True
                    else:
                        self.logit(None, f'----- Get Transaction result ... [{i}/{max_wait_sec}]') # noqa

                    i += 1
                if i >= max_wait_sec:
                    self.logit('testnet_mint', f'Transaction failed, took {i} seconds.') # noqa
                    return False
        return False

    def faucet_mint(self):
        """
        """
        for i in range(1, DEF_NUM_TRY):
            self.logit('faucet_mint', f'Faucet Summit try_i={i}/{DEF_NUM_TRY}')

            if self.init_okx() is False:
                continue

            self.page.get('https://dev.app.spindlefinance.xyz/mint')
            # self.page.wait.load_start()
            self.page.wait(3)

            self.logit('faucet_mint', f'tabs_count={self.page.tabs_count}')

            ele_info = self.page.ele('Terms of Services', timeout=2)
            if not isinstance(ele_info, NoneElement):
                self.logit('faucet_mint', 'Terms of Services [Select]') # noqa
                ele_btn = self.page.ele('@@tag()=button@@role=checkbox', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.page.wait(1)

                    ele_btn = self.page.ele('@@tag()=button@@text()=Accept', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        self.page.wait(1)

            # 钱包未连接
            ele_btn = self.page.ele('@@tag()=button@@text()=Connect Wallet', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                self.logit('faucet_mint', 'Need to Connect Wallet ...') # noqa
                ele_btn.click(by_js=True)
                self.page.wait(1)
                ele_btn = self.page.ele('@@tag()=div@@class:iekbcc0 ju367v4@@text()=OKX Wallet', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.page.wait(1)

                    # OKX Wallet Connect
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
                self.logit('faucet_mint', 'Wrong network ...')
                ele_btn.click(by_js=True)
                self.page.wait(1)
                ele_btn = self.page.ele('@@tag()=button@@text()=Botanix Testnet', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    self.logit('faucet_mint', 'Select Botanix Testnet ...')
                    ele_btn.click(by_js=True)
                    self.page.wait(1)

                    # Approve
                    if len(self.page.tab_ids) == 2:
                        tab_id = self.page.latest_tab
                        tab_new = self.page.get_tab(tab_id)
                        ele_btn = tab_new.ele('@@tag()=button@@data-testid=okd-button@@text()=Approve', timeout=2) # noqa
                        if not isinstance(ele_btn, NoneElement):
                            ele_btn.click(by_js=True)
                            self.logit('faucet_mint', 'Approve Botanix Testnet ...') # noqa
                            self.page.wait(1)

            # 钱包已连接
            ele_btn = self.page.ele('@@tag()=button@@class:inline-flex items-center@@text():…', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                self.logit('faucet_mint', 'Wallet is connected')
            else:
                self.logit('faucet_mint', 'Wallet is failed to connected [ERROR]') # noqa
                continue

            is_success = False
            n_mint = random.randint(DEF_MINT_USDC_MIN, DEF_MINT_USDC_MAX)
            for i in range(n_mint):
                self.logit('faucet_mint', f'*** Mint USDC {i+1}/{n_mint}')
                ret = self.testnet_mint('USDC')
                is_success = is_success or ret

            n_mint = random.randint(DEF_MINT_WBTC_MIN, DEF_MINT_WBTC_MAX)
            for i in range(n_mint):
                self.logit('faucet_mint', f'*** Mint WBTC {i+1}/{n_mint}')
                ret = self.testnet_mint('WBTC')
                is_success = is_success or ret

            if is_success:
                logger.info('Mint success!')
                self.logit('faucet_mint', 'Mint success!')
                return True

            # logger.info(f'Submit failed, took {i} seconds.')

            # self.save_screenshot(name='s1_004.jpg')
            # d_cont = {
            #     'title': 'Faucet Submit Failed! [getbotanixfunds]',
            #     'text': (
            #         'Faucet Submit Failed [getbotanixfunds]\n'
            #         '- {}\n'
            #         .format(self.args.s_profile)
            #     )
            # }
            # ding_msg(d_cont, DEF_DING_TOKEN, msgtype="markdown")
            # continue

        self.logit('faucet_mint', 'Mint failed!')
        self.close()
        return False


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

    while profiles:
        n += 1
        logger.info('#'*40)
        s_profile = random.choice(profiles)
        logger.info(f'progress:{n}/{total} [{s_profile}]') # noqa
        profiles.remove(s_profile)

        args.s_profile = s_profile

        if s_profile not in instSpindleTask.dic_purse:
            logger.info(f'{s_profile} is not in purse conf [ERROR]')
            sys.exit(0)

        def _run():
            instSpindleTask.initChrome(args.s_profile)
            instSpindleTask.init_okx()
            instSpindleTask.close()
            instSpindleTask.initChrome(args.s_profile)
            is_claim = instSpindleTask.faucet_mint()
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

        logger.info(f'[{s_profile}] Finish')

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
