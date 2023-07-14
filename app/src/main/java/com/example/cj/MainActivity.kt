package com.example.cj

import android.content.Intent
import androidx.appcompat.app.AppCompatActivity
import android.os.Bundle
import com.example.cj.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {
    private var mBinding: ActivityMainBinding? = null
    //매번 null 체크하지 않도록 확인 후 재 선언
    private val binding get() = mBinding!!

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        //setContentView(R.layout.activity_main)

        mBinding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val intent = Intent(this,StopboxMain::class.java)
        binding.mainBtn1.setOnClickListener{startActivity(intent)}

        val intent2 = Intent(this,ConveyorMain::class.java)
        binding.mainBtn2.setOnClickListener{startActivity(intent2)}



    }

    // 액티비티 파괴
    override fun onDestroy() {
        // onDestroy 에서 binding class 인스턴스 참조를 정리
        mBinding = null
        super.onDestroy()
    }

}