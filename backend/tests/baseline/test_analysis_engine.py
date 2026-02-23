from app.services import analysis_engine

def test_analysis_engine_importable():
    # 仅验证模块与关键函数可导入，作为 Phase0 基线
    assert hasattr(analysis_engine, "run_analysis")
    assert callable(analysis_engine.run_analysis)
