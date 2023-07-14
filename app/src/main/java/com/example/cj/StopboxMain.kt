package com.example.cj

import android.content.Intent
import androidx.appcompat.app.AppCompatActivity
import android.os.Bundle
import com.example.cj.databinding.ActivityStopboxMainBinding

class StopboxMain : AppCompatActivity() {

    private var mBinding: ActivityStopboxMainBinding? = null
    //매번 null 체크하지 않도록 확인 후 재 선언
    private val binding get() = mBinding!!

    override fun onCreate(savedInstanceState: Bundle?) {

        super.onCreate(savedInstanceState)
        //setContentView(R.layout.activity_stopbox_main)

        mBinding = ActivityStopboxMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val intent = Intent(this,MainActivity::class.java)
        binding.backbtn.setOnClickListener{startActivity(intent)}
    }

}