def place_order(self, *args, **kwargs): # <- 여기만 *args, **kwargs 로 변경!
    from config_live import can_place_real_order
    import os
    import sys

    # 실거래일 때만 체크
    if hasattr(self, 'is_real_mode') and self.is_real_mode:
        ok, msg = can_place_real_order(
            current_filename=os.path.basename(sys.argv[0]),
            pin_input=getattr(self, 'pin_input', '')
        )
        if not ok:
            print(f"[차단] 실주문 차단됨: {msg}")
            return None

    # --- 여기부터 네 기존 place_order 로직 이어서 작성 ---
    # self.api.order(...) 같은 원래 코드